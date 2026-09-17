"""
文献研究类型 AI 分类服务
使用 DeepSeek API 对文献进行研究类型判定
"""

import json
import os
import logging
from typing import Dict, Optional, List
from openai import OpenAI

logger = logging.getLogger(__name__)

# AI 分类 Prompt
LITERATURE_CLASSIFY_PROMPT = """你是医学文献研究类型判定助手。

任务：
根据文献标题、摘要、关键词，判断该文献属于以下哪一种研究类型：
1. epidemiology：流行病学研究，如横断面研究、队列研究、病例对照研究、人群患病率/风险因素分析等
2. in-vivo：体内实验，如动物实验、活体暴露实验、体内毒理或致敏实验
3. in-vitro：体外实验，如细胞实验、组织培养、器官外实验、分子机制体外验证

判定要求：
1. 必须严格依据标题和摘要内容判断，不能凭常识猜测
2. 如果摘要明确出现 human subjects、patients、cohort、case-control、prevalence、incidence 等，优先判为 epidemiology
3. 如果明确出现 mice、rats、rabbit、animal model、in vivo、murine 等，判为 in-vivo
4. 如果明确出现 cell line、keratinocyte、fibroblast、macrophage、in vitro、cell culture 等，判为 in-vitro
5. 如果信息不足，或者不是上面这三种则判定为other，并在 reason 中说明依据不足

输出严格 JSON，不要有任何额外文字。

JSON格式：
{
  "study_type": "epidemiology | in-vivo | in-vitro | other",
  "reason": "简要说明判断依据"
}"""


class LiteratureClassifier:
    """文献研究类型 AI 分类器"""

    def __init__(self):
        self.api_key = os.environ.get('OPENAI_API_KEY', '')
        self.base_url = "https://api.deepseek.com/v1"
        self.model = "deepseek-chat"
        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)

    def classify_single(self, title: str, abstract: str = '', keywords: str = '') -> Dict:
        """
        对单篇文献进行研究类型分类
        
        Args:
            title: 文献标题
            abstract: 文献摘要
            keywords: 文献关键词
            
        Returns:
            dict: {"study_type": "...", "reason": "..."}
        """
        user_content = f"标题：{title}\n"
        if abstract:
            user_content += f"摘要：{abstract}\n"
        if keywords:
            user_content += f"关键词：{keywords}\n"

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": LITERATURE_CLASSIFY_PROMPT},
                    {"role": "user", "content": user_content}
                ],
                max_tokens=200,
                temperature=0.1
            )
            content = response.choices[0].message.content.strip()
            # 尝试解析 JSON
            result = json.loads(content)
            # 校验 study_type 合法性
            valid_types = ['epidemiology', 'in-vivo', 'in-vitro', 'other']
            if result.get('study_type') not in valid_types:
                result['study_type'] = 'other'
            return result
        except json.JSONDecodeError as e:
            logger.warning(f"AI 返回内容无法解析为 JSON: {content}, error: {e}")
            return {"study_type": "other", "reason": "AI返回格式异常"}
        except Exception as e:
            logger.error(f"AI 分类调用失败: {e}")
            return {"study_type": "other", "reason": f"AI调用异常: {str(e)}"}

    def classify_batch(self, items: List[Dict]) -> List[Dict]:
        """
        批量对文献进行分类
        
        Args:
            items: 文献列表，每项需包含 title，可选 abstract、keywords
            
        Returns:
            list: 每项为 {"study_type": "...", "reason": "..."}
        """
        results = []
        for i, item in enumerate(items):
            title = item.get('title') or item.get('title_zh') or ''
            abstract = item.get('abstract') or item.get('abstract_zh') or ''
            keywords = item.get('keywords') or ''
            
            result = self.classify_single(title, abstract, keywords)
            results.append(result)
            
            if (i + 1) % 10 == 0:
                logger.info(f"AI 分类进度: {i + 1}/{len(items)}")
        
        return results
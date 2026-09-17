import os
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

# 固定绝对路径
base_dir = r"D:\stresor_data"
chroma_path = os.path.join(base_dir, "chroma_db")
model_path = os.path.join(base_dir, "models", "all-MiniLM-L6-v2")

class VectorDatabase:
    """向量库封装类"""
    
    def __init__(self):
        self.chroma_client = None
        self.collection = None
        self.embedding_model = None
        self.openai_client = None
        self.initialized = False
        self.initialization_started = False
        
        # 配置
        self.CHROMA_DB_PATH = chroma_path
        self.COLLECTION_NAME = "literature_collection"
        self.EMBEDDING_MODEL = model_path  # 使用本地模型
        self.OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')
        self.DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"
        self.DEEPSEEK_MODEL = "deepseek-chat"
        
        # 设置环境变量解决符号链接问题
        os.environ['HF_HUB_DISABLE_SYMLINKS_WARNING'] = '1'
        os.environ['HF_HUB_DISABLE_SYMLINKS'] = '1'
        
        # 不立即初始化，改为真正的延迟加载
        # self._initialize()
    
    def _initialize(self):
        """初始化向量库和模型"""
        # 模型文件不存在时快速失败，避免无谓加载 torch（重依赖，易 OOM）
        if not os.path.exists(self.EMBEDDING_MODEL):
            logger.warning(f"嵌入模型路径不存在，跳过向量库初始化: {self.EMBEDDING_MODEL}")
            self.initialized = False
            return
        try:
            # 懒加载重依赖：仅在真正使用知识问答时才导入，避免启动时占用大量内存
            from sentence_transformers import SentenceTransformer
            import chromadb
            from openai import OpenAI
            logger.info("开始初始化向量库...")
            
            # 使用本地模型路径直接加载
            logger.info(f"加载本地模型: {self.EMBEDDING_MODEL}")
            self.embedding_model = SentenceTransformer(self.EMBEDDING_MODEL)
            logger.info("嵌入模型加载完成")
            
            # 初始化 ChromaDB
            logger.info(f"连接 ChromaDB: {self.CHROMA_DB_PATH}")
            self.chroma_client = chromadb.PersistentClient(path=self.CHROMA_DB_PATH)
            self.collection = self.chroma_client.get_collection(self.COLLECTION_NAME)
            
            # 初始化 OpenAI 客户端
            logger.info("初始化 OpenAI 客户端...")
            self.openai_client = OpenAI(
                api_key=self.OPENAI_API_KEY,
                base_url=self.DEEPSEEK_BASE_URL
            )
            logger.info("OpenAI 客户端初始化完成")
            
            self.initialized = True
            logger.info("向量库初始化成功")
            
        except Exception as e:
            logger.error(f"向量库初始化失败: {e}")
            self.initialized = False
    
    def is_available(self) -> bool:
        """检查向量库是否可用"""
        if not self.initialized and not self.initialization_started:
            self.initialization_started = True
            try:
                logger.info("开始初始化向量数据库...")
                self._initialize()
                logger.info("向量数据库初始化完成")
            except Exception as e:
                logger.error(f"延迟初始化失败: {e}")
                return False
        return self.initialized
    
    def query_documents(self, question: str, n_results: int = 3) -> List[str]:
        """检索相关文档"""
        if not self.is_available():
            return [] 
        
        # 原始查询代码（暂时注释）
        try:
            # 将问题编码为向量
            query_emb = self.embedding_model.encode(question).tolist()
            
            # 检索最相关的文档（简化版本，直接尝试查询）
            logger.info("开始文档检索...")
            results = self.collection.query(
                query_embeddings=[query_emb], 
                n_results=n_results
            )
            
            # 提取文档内容
            documents = results.get("documents", [[]])[0]
            logger.info(f"检索到 {len(documents)} 个相关文档")
            return documents
                    
        except Exception as e:
            logger.error(f"文档检索失败: {e}")

            # 检查是否是维度不匹配问题
            if "dimension" in str(e) and "384" in str(e) and "768" in str(e):
                logger.warning("检测到向量维度不匹配问题，ChromaDB集合期望768维，但当前模型输出384维")
            
            # 返回一些示例文档作为降级处理
            return [
                "过敏原是指能够引起过敏反应的物质，包括食物、药物、花粉等。",
                "常见的过敏原有花粉、尘螨、动物毛发、某些食物等。",
                "过敏反应是免疫系统对过敏原的过度反应。"
            ]
    
    def _ensure_llm(self) -> bool:
        """初始化 DeepSeek/OpenAI 客户端（轻量，独立于向量库，避免加载 torch）。"""
        if self.openai_client is not None:
            return True
        try:
            from openai import OpenAI
            self.openai_client = OpenAI(
                api_key=self.OPENAI_API_KEY,
                base_url=self.DEEPSEEK_BASE_URL
            )
            logger.info("DeepSeek 客户端初始化完成")
            return True
        except Exception as e:
            logger.error(f"DeepSeek 客户端初始化失败: {e}")
            return False

    def generate_answer(self, question: str, context_documents: List[str]) -> Optional[str]:
        """使用 DeepSeek 生成答案（仅依赖 LLM，不依赖向量库）。"""
        if not self._ensure_llm():
            return None

        try:
            # 构建上下文
            context = "\n".join([d for d in context_documents if d])

            # 构建提示词（无上下文时让模型基于自身知识回答）
            if context:
                prompt = f"""你是一名专业的科学助手，专门回答关于过敏原安全、产品安全、毒性数据等科学问题。

请根据以下检索到的资料回答问题：

资料：
{context}

问题：{question}

快速回答总结。"""
            else:
                prompt = f"""你是一名专业的科学助手，专门回答关于过敏原安全、产品安全、毒性数据等科学问题。

请直接回答以下问题（如无相关资料，请基于你的知识回答）：

问题：{question}

快速回答总结。"""

            # 调用 DeepSeek API
            response = self.openai_client.chat.completions.create(
                model=self.DEEPSEEK_MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1000,
                temperature=0.3
            )

            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"DeepSeek API 调用失败: {e}")
            return None

# 全局向量库实例
_vector_db = None

def get_vector_database() -> VectorDatabase:
    """获取向量库实例（单例模式）"""
    global _vector_db
    if _vector_db is None:
        _vector_db = VectorDatabase()
    return _vector_db
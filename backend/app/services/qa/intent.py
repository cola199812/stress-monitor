from __future__ import annotations

def extract_subject_and_intent(q: str) -> tuple[str | None, str]:
    s = (q or '').strip()
    for ch in ('？', '?', '。', '.', '！', '!'):
        s = s.replace(ch, '')
    # 清理斜杠组合问法（如 成分/过敏原）
    s = s.replace('/', '')
    # 去除"询问/请问/关于"前缀
    for pfx in ('询问', '请问', '关于'):
        if s.startswith(pfx):
            s = s[len(pfx):].strip()
    # 去除尾部"哪些/什么/哪一些"等泛指词
    for suf in ('哪些', '什么', '哪一些', '哪类', '哪种'):
        if s.endswith(suf):
            s = s[: -len(suf)].strip()
    # 去除尾部"相关/有关"
    for suf2 in ('相关', '有关'):
        if s.endswith(suf2):
            s = s[: -len(suf2)].strip()

    # 过敏原/成分/致敏物/配方/材料
    for key in ('过敏原', '成分', '致敏物', '配方', '材料', '成份'):
        if key in s:
            subj = s.split(key)[0]
            for suf in ('有哪些', '有哪一些', '主要', '常见的', '常见', '代表', '典型'):
                subj = subj.replace(suf, '')
            subj = subj.replace('的', '').strip()
            return (subj or None, 'allergens')

    # 症状/危害/不良反应/风险
    if any(k in s for k in ('症状', '危害', '风险', '不良反应', '副作用')):
        subj = s.split('症状')[0] if '症状' in s else s
        for seg in ('可能引发', '会引发', '会造成', '可能造成', '有哪些', '有哪一些', '代表', '典型', '主要'):
            subj = subj.replace(seg, '')
        subj = subj.replace('的', '').strip()
        return (subj or None, 'symptoms')

    # 文献/论文/研究
    if any(k in s for k in ('文献', '论文', '研究', '学术文献', '参考文献', '佐证文献', '研究报告')):
        subj = s.split('文献')[0] if '文献' in s else (s.split('论文')[0] if '论文' in s else s.split('研究')[0])
        for seg in ('相关的', '有哪些', '有哪一些', '代表', '典型', '主要', '关于'):
            subj = subj.replace(seg, '')
        subj = subj.replace('的', '').strip()
        return (subj or None, 'literature')

    # 新闻/报道/资讯
    if any(k in s for k in ('新闻', '报道', '媒体报道', '新闻报道', '资讯', '消息')):
        subj = s.split('新闻')[0] if '新闻' in s else (s.split('报道')[0] if '报道' in s else s.split('资讯')[0])
        for seg in ('相关的', '有哪些', '有哪一些', '代表', '典型', '主要', '关于'):
            subj = subj.replace(seg, '')
        subj = subj.replace('的', '').strip()
        return (subj or None, 'news')

    # 召回/缺陷/质量问题
    if any(k in s for k in ('召回', '召回信息', '产品召回', '召回通知', '召回公告', '缺陷', '安全隐患', '质量问题')):
        subj = s.split('召回')[0] if '召回' in s else (s.split('缺陷')[0] if '缺陷' in s else s.split('质量问题')[0])
        for seg in ('相关的', '有哪些', '有哪一些', '代表', '典型', '主要', '关于'):
            subj = subj.replace(seg, '')
        subj = subj.replace('的', '').strip()
        return (subj or None, 'recall')

    # 产品/商品/品牌/型号
    if any(k in s for k in ('产品', '商品', '品牌', '型号')):
        subj = s.split('产品')[0] if '产品' in s else s
        for seg in ('相关的', '有哪些', '有哪一些', '代表', '典型', '主要'):
            subj = subj.replace(seg, '')
        subj = subj.replace('的', '').strip()
        return (subj or None, 'products')

    return (None, 'generic')

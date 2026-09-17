from __future__ import annotations

from typing import Dict, List, Tuple, Any, Optional
import re

from .neo4j_client import Neo4jClient


def _primary_label(labels: List[str]) -> str:
    if not labels:
        return 'Node'
    # 优先返回第一标签
    return str(labels[0])


def _node_to_dict(n: Any) -> Dict[str, str]:
    labels = list(n.labels) if hasattr(n, 'labels') else []
    node_id = (
        str(getattr(n, 'element_id')) if hasattr(n, 'element_id') else (
            str(getattr(n, 'id')) if hasattr(n, 'id') else str(n.get('id', ''))
        )
    )
    name = n.get('name', '') if hasattr(n, 'get') else getattr(n, 'name', '')
    return {
        'id': node_id,
        'label': _primary_label(labels),
        'name': name or node_id,
    }


def _edge_to_dict(r: Any, start_id: str, end_id: str) -> Dict[str, str]:
    rtype = r.type if hasattr(r, 'type') else r.get('type', '')
    return {
        'from': start_id,
        'to': end_id,
        'type': str(rtype),
    }


def _append_type_filter(where_prefix: str, types: Optional[List[str]]) -> str:
    if types:
        return f" {where_prefix} type(r) IN $types "
    return ""


def query_graph_by_name(
    name: str,
    limit: int = 300,
    per_node: int = 50,
    types: Optional[List[str]] = None,
) -> Dict[str, List[Dict[str, str]]]:
    driver = Neo4jClient.get_driver()
    where_types = _append_type_filter("WHERE", types)
    cypher = f"""
        MATCH (center)
        WHERE toLower(replace(toString(center.name),' ','')) = toLower(replace($name,' ',''))
        WITH center LIMIT 1
        CALL (center) {{
            MATCH (center)-[r]-(m)
            {where_types}
            RETURN center AS n, r, m
            LIMIT $perNode
        }}
        RETURN n, r, m
        LIMIT $limit
    """
    nodes: Dict[str, Dict[str, str]] = {}
    edges: Dict[Tuple[str, str, str], Dict[str, str]] = {}
    with driver.session() as session:
        for record in session.run(cypher, name=name, limit=limit, perNode=per_node, types=types):
            n = record['n']
            m = record['m']
            r = record['r']
            n_dict = _node_to_dict(n)
            m_dict = _node_to_dict(m)
            nodes[n_dict['id']] = n_dict
            nodes[m_dict['id']] = m_dict
            start_id = n_dict['id']
            end_id = m_dict['id']
            edge_dict = _edge_to_dict(r, start_id, end_id)
            edges[(edge_dict['from'], edge_dict['to'], edge_dict['type'])] = edge_dict

    return {
        'nodes': list(nodes.values()),
        'edges': list(edges.values()),
    }


def query_neighbors_by_id(
    node_id: str,
    limit: int = 300,
    per_node: int = 50,
    types: Optional[List[str]] = None,
) -> Dict[str, List[Dict[str, str]]]:
    driver = Neo4jClient.get_driver()
    where_types = _append_type_filter("WHERE", types)
    cypher = f"""
        MATCH (center)
        WHERE elementId(center) = toString($id)
        WITH center
        CALL (center) {{
            MATCH (center)-[r]-(m)
            {where_types}
            RETURN center AS n, r, m
            LIMIT $perNode
        }}
        RETURN n, r, m
        LIMIT $limit
    """
    nodes: Dict[str, Dict[str, str]] = {}
    edges: Dict[Tuple[str, str, str], Dict[str, str]] = {}
    with driver.session() as session:
        for record in session.run(cypher, id=node_id, limit=limit, perNode=per_node, types=types):
            n = record['n']
            m = record['m']
            r = record['r']
            n_dict = _node_to_dict(n)
            m_dict = _node_to_dict(m)
            nodes[n_dict['id']] = n_dict
            nodes[m_dict['id']] = m_dict
            start_id = n_dict['id']
            end_id = m_dict['id']
            edge_dict = _edge_to_dict(r, start_id, end_id)
            edges[(edge_dict['from'], edge_dict['to'], edge_dict['type'])] = edge_dict

    return {
        'nodes': list(nodes.values()),
        'edges': list(edges.values()),
    }


def query_neighbors_by_id_smart(
    node_id: str,
    limit: int = 300,
    per_node: int = 50,
    types: Optional[List[str]] = None,
) -> Dict[str, List[Dict[str, str]]]:
    """
    智能邻居扩展：
    - 若中心节点为`类别`，展开两跳：
      类别-[包含产品]->产品 和 类别-[聚合过敏原]->过敏原-[可能导致]->症状
      同时包含中心与产品、过敏原之间的边。
    - 若中心节点为`过敏原`，展开多跳：
      产品-[包含过敏原]->过敏原-[可能导致]->症状-[佐证文献]->文献
    - 其他情况，回退到普通一跳邻居。
    """
    driver = Neo4jClient.get_driver()

    # 先探测标签
    detect_cypher = """
        MATCH (center)
        WHERE elementId(center) = toString($id)
        RETURN labels(center) AS labels, center AS center
        LIMIT 1
    """
    with driver.session() as session:
        rec = session.run(detect_cypher, id=node_id).single()
        if not rec:
            return { 'nodes': [], 'edges': [] }
        labels = rec["labels"] or []

    # 检查是否为过敏原节点
    if '过敏原' in labels:
        # 过敏原节点：通过过敏关系节点展开产品、症状、文献
        # 数据结构: 产品-[包含]->过敏关系-[关联]->过敏原
        #          过敏关系-[导致]->症状
        #          文献-[佐证文献]->过敏关系
        nodes: Dict[str, Dict[str, str]] = {}
        edges: Dict[Tuple[str, str, str], Dict[str, str]] = {}

        def _accumulate(records: List[Any]) -> None:
            for record in records:
                n = record['n']
                m = record['m']
                r = record['r']
                n_dict = _node_to_dict(n)
                m_dict = _node_to_dict(m)
                nodes[n_dict['id']] = n_dict
                nodes[m_dict['id']] = m_dict
                start_id = n_dict['id']
                end_id = m_dict['id']
                edge_dict = _edge_to_dict(r, start_id, end_id)
                edges[(edge_dict['from'], edge_dict['to'], edge_dict['type'])] = edge_dict

        where_types = _append_type_filter("WHERE", types)
        
        # 1) 通过过敏关系找到产品: 产品-[包含]->过敏关系-[关联]->过敏原
        cypher_allergen_to_relation_to_product = f"""
            MATCH (center:过敏原)
            WHERE elementId(center) = toString($id)
            MATCH (p:产品)-[r1:包含]->(rel:过敏关系)-[r2:关联]->(center)
            {where_types}
            RETURN p AS n, r1 AS r, rel AS m
            LIMIT $limit
        """

        # 1.5) 过敏关系节点本身也要显示
        cypher_allergen_to_relation = f"""
            MATCH (center:过敏原)
            WHERE elementId(center) = toString($id)
            MATCH (rel:过敏关系)-[r:关联]->(center)
            {where_types}
            RETURN rel AS n, r, center AS m
            LIMIT $limit
        """

        # 2) 通过过敏关系找到症状: 过敏关系-[导致]->症状
        cypher_relation_to_symptom = f"""
            MATCH (center:过敏原)
            WHERE elementId(center) = toString($id)
            MATCH (rel:过敏关系)-[r1:关联]->(center)
            MATCH (rel)-[r2:导致]->(s)
            WHERE ANY(label IN labels(s) WHERE label CONTAINS '症状')
            {where_types}
            RETURN rel AS n, r2 AS r, s AS m
            LIMIT $limit
        """

        # 3) 通过过敏关系找到文献: 文献-[佐证文献]->过敏关系
        cypher_literature_to_relation = f"""
            MATCH (center:过敏原)
            WHERE elementId(center) = toString($id)
            MATCH (rel:过敏关系)-[r1:关联]->(center)
            MATCH (l:文献)-[r2:佐证文献]->(rel)
            {where_types}
            RETURN l AS n, r2 AS r, rel AS m
            LIMIT $limit
        """

        with driver.session() as session:
            # 执行查询
            rs1 = session.run(cypher_allergen_to_relation_to_product, id=node_id, limit=limit, types=types)
            _accumulate(list(rs1))
            
            rs1_5 = session.run(cypher_allergen_to_relation, id=node_id, limit=limit, types=types)
            _accumulate(list(rs1_5))

            rs2 = session.run(cypher_relation_to_symptom, id=node_id, limit=limit, types=types)
            _accumulate(list(rs2))

            rs3 = session.run(cypher_literature_to_relation, id=node_id, limit=limit, types=types)
            _accumulate(list(rs3))

        return {
            'nodes': list(nodes.values()),
            'edges': list(edges.values()),
        }

    if '类别' not in labels:
        # 非类别、非过敏原节点，使用普通邻居
        return query_neighbors_by_id(node_id, limit=limit, per_node=per_node, types=types)

    # 类别节点：两跳展开
    nodes: Dict[str, Dict[str, str]] = {}
    edges: Dict[Tuple[str, str, str], Dict[str, str]] = {}

    def _accumulate(records: List[Any]) -> None:
        for record in records:
            n = record['n']
            m = record['m']
            r = record['r']
            n_dict = _node_to_dict(n)
            m_dict = _node_to_dict(m)
            nodes[n_dict['id']] = n_dict
            nodes[m_dict['id']] = m_dict
            start_id = n_dict['id']
            end_id = m_dict['id']
            edge_dict = _edge_to_dict(r, start_id, end_id)
            edges[(edge_dict['from'], edge_dict['to'], edge_dict['type'])] = edge_dict

    where_types = _append_type_filter("WHERE", types)
    cypher_category_expansion = f"""
        // 中心与产品
        MATCH (center)
        WHERE elementId(center) = toString($id)
        MATCH (center)-[r0:包含产品]->(p:产品)
        RETURN center AS n, r0 AS r, p AS m
        LIMIT $limit
    """

    cypher_category_to_allergen = f"""
        MATCH (center)
        WHERE elementId(center) = toString($id)
        MATCH (center)-[r1:聚合过敏原]->(chem:过敏原)
        {where_types}
        RETURN center AS n, r1 AS r, chem AS m
        LIMIT $limit
    """

    cypher_chemical_to_symptom = f"""
        MATCH (center)
        WHERE elementId(center) = toString($id)
        MATCH (center)-[:聚合过敏原]->(chem:过敏原)-[r2:可能导致]->(sym:症状)
        {where_types}
        RETURN chem AS n, r2 AS r, sym AS m
        LIMIT $limit
    """

    with driver.session() as session:
        # 1) 类别-产品
        rs1 = session.run(cypher_category_expansion, id=node_id, limit=limit)
        _accumulate(list(rs1))

        # 2) 类别-过敏原
        rs2 = session.run(cypher_category_to_allergen, id=node_id, limit=limit, types=types)
        _accumulate(list(rs2))

        # 3) 过敏原-症状
        rs3 = session.run(cypher_chemical_to_symptom, id=node_id, limit=limit, types=types)
        _accumulate(list(rs3))

    return {
        'nodes': list(nodes.values()),
        'edges': list(edges.values()),
    }

def _search_nodes_fulltext(q: str, index: str, limit: int) -> List[Any]:
    driver = Neo4jClient.get_driver()
    cypher = (
        """
        CALL db.index.fulltext.queryNodes($index, $q) YIELD node, score
        WHERE (node)--()
        RETURN node, score
        ORDER BY score DESC
        LIMIT $limit
        """
    )
    rows: List[Any] = []
    with driver.session() as session:
        for record in session.run(cypher, index=index, q=q, limit=limit):
            rows.append(record['node'])
    return rows


def _expand_synonyms(q: str, for_label: Optional[str] = None) -> List[str]:
    """简单中文归一化/同义词扩展，用于提升类别命中。
    - 去除常见人群限定词：儿童/婴童/婴儿/宝宝/婴幼儿/小孩/小朋友/kids
    - 统一括号与空格
    - 对类别标签：补全“产品”后缀；尝试只取括号外/主干部分
    """
    if not q:
        return []
    s = q.strip()
    s = s.replace('（', '(').replace('）', ')')
    s = re.sub(r"\s+", " ", s)
    # 移除人群限定词
    people_words = ["儿童", "婴童", "婴儿", "宝宝", "婴幼儿", "小孩", "小朋友", "kids", "儿童用"]
    base = s
    for w in people_words:
        base = base.replace(w, "")
    base = base.strip()
    variants: List[str] = []
    variants.append(s)
    if base and base != s:
        variants.append(base)
    # 只取括号外主干
    main = re.split(r"\s*\(", base)[0].strip()
    if main and main not in variants:
        variants.append(main)
    # 类别常见后缀
    if for_label == '类别':
        if not main.endswith('产品') and (main + '产品') not in variants:
            variants.append(main + '产品')
        # 自定义类别同义词映射（可按需扩展）
        # 注意：键或其主干命中时，将值加入候选；用于提高命中率
        custom_map: Dict[str, List[str]] = {
            # 修正/涂改类
            '修正文具': ['修正', '修正液', '涂改液', '修正带'],
            '修正液': ['修正文具', '涂改液', '修正带', '修正'],
            '涂改液': ['修正文具', '修正液', '修正带', '修正'],
            '修正带': ['修正文具', '修正液', '涂改液', '修正'],
            # 儿童地垫
            '儿童地垫': ['泡沫垫', '爬行垫', '地垫', 'EVA地垫'],
            # 空气清新剂/香薰类
            '空气清新剂': ['香薰', '芳香剂', '空气芳香', '空气香氛'],
            '香薰': ['空气清新剂', '芳香剂'],
            '芳香剂': ['空气清新剂', '香薰'],
            # 驱蚊类（统一到“驱蚊产品”）
            '驱蚊产品': ['驱蚊液', '驱蚊剂', '防蚊喷雾', '防蚊液', '避蚊胺', 'DEET', '花露水'],
            '驱蚊液': ['驱蚊产品', '驱蚊剂', '防蚊喷雾', '防蚊液', '避蚊胺', 'DEET', '花露水'],
            '驱蚊剂': ['驱蚊产品', '驱蚊液', '防蚊喷雾', '防蚊液', '避蚊胺', 'DEET', '花露水'],
            '防蚊喷雾': ['驱蚊产品', '驱蚊液', '驱蚊剂', '防蚊液'],
            '防蚊液': ['驱蚊产品', '驱蚊液', '驱蚊剂', '防蚊喷雾'],
            '避蚊胺': ['驱蚊产品', '驱蚊液', '驱蚊剂'],
            '花露水': ['驱蚊产品'],
        }
        for key, vals in custom_map.items():
            if key in s or key == main:
                for v in vals:
                    if v not in variants:
                        variants.append(v)
    # 去重保序
    uniq: List[str] = []
    seen: set[str] = set()
    for v in variants:
        if v and v not in seen:
            seen.add(v)
            uniq.append(v)
    return uniq


def search_nodes(q: str, label: str | None = None, limit: int = 50, mode: str = 'auto', synonyms: bool = False) -> List[Dict[str, str]]:
    driver = Neo4jClient.get_driver()
    results: List[Dict[str, str]] = []

    has_cjk = bool(re.search(r"[\u4e00-\u9fff]", q or ""))

    # 优先全文索引（英文/字母/数字更有效）；中文默认跳过全文索引以避免误命中
    if (mode == 'fulltext') or (mode == 'auto' and not has_cjk):
        # 先中文索引，再英文索引
        for idx in ('idx_node_name_cn', 'idx_node_name'):
            try:
                nodes = _search_nodes_fulltext(q + '~', idx, limit)
                for n in nodes:
                    results.append(_node_to_dict(n))
                if results:
                    return results
            except Exception:
                continue

    # 回退：优先指定标签顺序检索，中文优先前缀，再包含；不再强制有边
    label_priority: List[str] = ['类别', '产品', '过敏原', '症状']
    with driver.session() as session:
        if label:
            queries = _expand_synonyms(q, for_label=label) if synonyms else [q]
            remaining = limit
            for cand in queries:
                if remaining <= 0:
                    break
                cypher_starts = "MATCH (n:%s) WHERE toLower(replace(toString(n.name),' ','')) STARTS WITH toLower(replace($q,' ','')) RETURN n LIMIT $limit" % label
                rows = list(session.run(cypher_starts, q=cand, limit=remaining))
                for record in rows:
                    results.append(_node_to_dict(record['n']))
                remaining = max(0, limit - len(results))
                if remaining <= 0:
                    break
                cypher_contains = "MATCH (n:%s) WHERE toLower(replace(toString(n.name),' ','')) CONTAINS toLower(replace($q,' ','')) RETURN n LIMIT $limit" % label
                rows2 = list(session.run(cypher_contains, q=cand, limit=remaining))
                for record in rows2:
                    results.append(_node_to_dict(record['n']))
                remaining = max(0, limit - len(results))
        else:
            remaining = limit
            for lb in label_priority:
                if remaining <= 0:
                    break
                queries = _expand_synonyms(q, for_label=lb) if synonyms else [q]
                for cand in queries:
                    if remaining <= 0:
                        break
                    # 前缀优先
                    cypher_lb_prefix = "MATCH (n:%s) WHERE toLower(replace(toString(n.name),' ','')) STARTS WITH toLower(replace($q,' ','')) RETURN n LIMIT $limit" % lb
                    rows = list(session.run(cypher_lb_prefix, q=cand, limit=remaining))
                    for record in rows:
                        results.append(_node_to_dict(record['n']))
                    remaining = max(0, limit - len(results))
                    if remaining <= 0:
                        break
                    # 再包含
                    cypher_lb_contains = "MATCH (n:%s) WHERE toLower(replace(toString(n.name),' ','')) CONTAINS toLower(replace($q,' ','')) RETURN n LIMIT $limit" % lb
                    rows2 = list(session.run(cypher_lb_contains, q=cand, limit=remaining))
                    for record in rows2:
                        results.append(_node_to_dict(record['n']))
                    remaining = max(0, limit - len(results))

            # 若仍不足，再做一次无标签的模糊匹配兜底
            if len(results) < limit:
                cypher_all = "MATCH (n) WHERE toLower(replace(toString(n.name),' ','')) CONTAINS toLower(replace($q,' ','')) RETURN n LIMIT $limit"
                for record in session.run(cypher_all, q=q, limit=limit - len(results)):
                    results.append(_node_to_dict(record['n']))

    # 去重（保持顺序）
    seen: set[str] = set()
    unique: List[Dict[str, str]] = []
    for item in results:
        item_id = item.get('id', '')
        if item_id in seen:
            continue
        seen.add(item_id)
        unique.append(item)
    return unique



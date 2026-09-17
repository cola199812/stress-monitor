from flask import Blueprint, request, jsonify
from datetime import datetime
from sqlalchemy.exc import IntegrityError
import hashlib
import json
import logging
import re
from app.services.translator import translate_to_en
from .. import db
from ..models import (
    Literature, LiteratureFilter, Product, AllergenSymptom,
    LiteratureEpiScoring, LiteratureVivoScoring, LiteratureVitroScoring,
    AllergenSymptomSource, Allergen, Symptom3, Symptom2
)

# 延迟导入的服务模块（避免循环导入）
try:
    from ..services.neo4j_sync import sync_to_neo4j
except ImportError:
    sync_to_neo4j = None

try:
    from app.services.crawler.pubmed import pubmed as pubmed_crawler
except ImportError:
    pubmed_crawler = None

try:
    from app.services.baidu_translation_service import BaiduTranslationService
except ImportError:
    BaiduTranslationService = None

try:
    from app.services.crawler.literature.pubmed_api import pubmed_api_crawler
except ImportError:
    pubmed_api_crawler = None

try:
    from app.services.ai_clasify.literature import LiteratureClassifier
except ImportError:
    LiteratureClassifier = None


bp = Blueprint('literature', __name__)


@bp.post('/create')
def create_literature():
    """创建新文献并绑定实体关系"""
    
    try:
        data = request.get_json()
        print(f'[Literature Create] 接收到的数据: {data}')
        
        # 提取基本信息和实体关系
        basic_info = data.get('basicInfo', {})
        entity_relations = data.get('entityRelations', [])
        
        # 从基本信息中获取文献类型
        literature_type = basic_info.get('literatureType', 'epidemiology')
        
        # 处理发布日期
        publish_date = None
        if basic_info.get('publishDate') and basic_info.get('publishDate').strip():
            try:
                publish_date = datetime.strptime(basic_info.get('publishDate'), '%Y-%m-%d').date()
            except Exception:
                publish_date = None

        has_state = False
        if entity_relations:
            has_state = True

        # 创建文献记录
        literature = Literature(
            title=basic_info.get('title', ''),
            source=basic_info.get('source', ''),
            pmid=basic_info.get('pmid', ''),
            authors=basic_info.get('authors', ''),
            publish_date=publish_date,
            abstract=basic_info.get('abstract', ''),
            link=basic_info.get('link', ''),
            state=has_state,  # 初始状态为未处理
            literature_type=literature_type
        )
        
        db.session.add(literature)
        db.session.flush()  # 获取文献ID
        
        print(f'[Literature Create] 文献已创建，ID: {literature.id}')
        
        # 处理实体关系
        created_relations = []
        for relation_data in entity_relations:
            allergen_id = relation_data.get('allergenId')
            symptom_id = relation_data.get('symptomId')
            scoring_data = relation_data.get('scoringData', {})
            
            # 1. 验证化学应激源-症状关系是否存在
            allergen_symptom = AllergenSymptom.query.filter_by(
                allergen_id=allergen_id,
                symptom_id=symptom_id
            ).first()
            
            is_new_relation = False
            
            # 2. 如果关系不存在，创建新关系
            if not allergen_symptom:
                print(f'[Literature Create] 关系不存在，创建新关系')
                allergen_symptom = AllergenSymptom(
                    allergen_id=allergen_id,
                    symptom_id=symptom_id
                )
                db.session.add(allergen_symptom)
                db.session.flush()
                is_new_relation = True
                
                # 重新查询以确保获取正确的关系ID
                allergen_symptom = AllergenSymptom.query.filter_by(
                    allergen_id=allergen_id,
                    symptom_id=symptom_id
                ).first()
                
                print(f'[Literature Create] 新关系已创建，ID: {allergen_symptom.id}')
            else:
                print(f'[Literature Create] 关系已存在，ID: {allergen_symptom.id}')
            
            # 3. 如果是新创建的关系，同步到Neo4j
            if is_new_relation:
                try:
                    from ..services.neo4j_sync import Neo4jSyncService
                    Neo4jSyncService.sync_allergen_symptom_relation(
                        allergen_id=allergen_id,
                        symptom_id=symptom_id,
                        relation_id=allergen_symptom.id,
                        operation='create'
                    )
                    print(f'[Literature Create] 关系已同步到Neo4j，relation_id: {allergen_symptom.id}')
                except Exception as e:
                    print(f'[Literature Create] Neo4j同步失败: {e}')
            
            # 3. 创建文献佐证关联
            literature_source = AllergenSymptomSource(
                allergen_symptom_id=allergen_symptom.id,
                literature_id=literature.id,
                evidence_strength=1.0
            )
            db.session.add(literature_source)
            db.session.flush()
            
            print(f'[Literature Create] 文献佐证已创建，ID: {literature_source.id}')
            
            # 4. 保存评分数据到对应的表
            if scoring_data and scoring_data.get('concentrationWeight'):
                print(f'[Literature Create] 保存评分数据，文献类型: {literature_type}')
                
                if literature_type == 'epidemiology':
                    _save_epidemiology_scoring(literature.id, allergen_symptom.id, scoring_data)
                elif literature_type == 'in-vivo':
                    _save_in_vivo_scoring(literature.id, allergen_symptom.id, scoring_data)
                elif literature_type == 'in-vitro':
                    _save_in_vitro_scoring(literature.id, allergen_symptom.id, scoring_data)
                
                # 有评分数据则标记为已处理
                literature.state = True
            
            created_relations.append({
                'allergen_symptom_id': allergen_symptom.id,
                'literature_source_id': literature_source.id
            })
        
        db.session.commit()
        
        print(f'[Literature Create] 文献创建成功，共创建 {len(created_relations)} 个关系')
        
        return jsonify({
            'success': True,
            'message': '文献创建成功',
            'data': {
                'id': literature.id,
                'title': literature.title,
                'literature_type': literature.literature_type,
                'relations_count': len(created_relations)
            }
        }), 201
        
    except Exception as e:
        db.session.rollback()
        print(f'[Literature Create] 创建失败: {str(e)}')
        return jsonify({
            'success': False,
            'message': f'创建文献失败: {str(e)}'
        }), 500


@bp.get('/')
def list_literature():
    """获取所有文献列表"""
    logger = logging.getLogger(__name__)
    
    page = int(request.args.get('page', 1) or 1)
    page_size_param = request.args.get('pageSize')
    
    # 如果没有传递pageSize参数，返回所有数据
    if page_size_param is None:
        page_size = None  # 不限制数量
        page = 1  # 重置为第一页
    else:
        page_size = int(page_size_param or 100)
        page_size = max(1, min(200, page_size))
    
    logger.info(f'[Literature] 查询参数 - page: {page}, pageSize: {page_size}')
    
    # 先获取总数（不包含ORDER BY，避免MySQL子查询计数问题）
    total = Literature.query.count()
    
    # 按发布时间倒序排列（MySQL兼容方式：使用CASE将NULL值排在最后）
    from sqlalchemy import case
    nulls_last = case((Literature.publish_date.is_(None), 1), else_=0)
    q = Literature.query.order_by(nulls_last.asc(), Literature.publish_date.desc(), Literature.id.desc())
    
    # 如果没有分页限制，返回所有数据
    if page_size is None:
        items = q.all()
    else:
        items = q.offset((page - 1) * page_size).limit(page_size).all()
    
    logger.info(f'[Literature] 查询结果总数: {total}, 返回 {len(items)} 条记录')
    
    def to_dict(x: Literature):
        # 获取实体关系信息 - 现在通过AllergenSymptomSource表
        literature_entity_relations = []
        try:
            # 查询该文献的所有实体关系
            source_relations = db.session.query(AllergenSymptomSource, AllergenSymptom, Allergen, Symptom2).join(
                AllergenSymptom, AllergenSymptomSource.allergen_symptom_id == AllergenSymptom.id
            ).join(
                Allergen, AllergenSymptom.allergen_id == Allergen.id
            ).join(
                Symptom2, AllergenSymptom.symptom_id == Symptom2.id
            ).filter(
                AllergenSymptomSource.literature_id == x.id
            ).all()
            
            for _, allergen_symptom, allergen, symptom2 in source_relations:
                # 加载评分数据
                scoring_data = {}
                if x.literature_type == 'epidemiology':
                    scoring = LiteratureEpiScoring.query.filter_by(
                        literature_id=x.id,
                        relation_id=allergen_symptom.id
                    ).first()
                    if scoring:
                        scoring_data = _get_epidemiology_scoring_data(scoring)
                elif x.literature_type == 'in-vivo':
                    scoring = LiteratureVivoScoring.query.filter_by(
                        literature_id=x.id,
                        relation_id=allergen_symptom.id
                    ).first()
                    if scoring:
                        scoring_data = _get_in_vivo_scoring_data(scoring)
                elif x.literature_type == 'in-vitro':
                    scoring = LiteratureVitroScoring.query.filter_by(
                        literature_id=x.id,
                        relation_id=allergen_symptom.id
                    ).first()
                    if scoring:
                        scoring_data = _get_in_vitro_scoring_data(scoring)
                
                literature_entity_relations.append({
                    'relation': f"{allergen.name} → {symptom2.symptom_name}",
                    'type': 'allergen-symptom',
                    'allergen_id': allergen_symptom.allergen_id,
                    'symptom_id': allergen_symptom.symptom_id,
                    'allergen_name': allergen.name,
                    'symptom_name': symptom2.symptom_name,
                    'scoringData': scoring_data
                })
        except Exception as e:
            logger.warning(f"查询文献 {x.id} 的实体关系失败: {e}")
        
        # 保持向后兼容性，返回第一个关系作为entityRelation
        entity_relation = None
        if literature_entity_relations:
            first_relation = literature_entity_relations[0]
            entity_relation = {
                'id': None,  # 保持兼容性
                'allergen_id': first_relation['allergen_id'],
                'symptom_id': first_relation['symptom_id'],
                'allergen_name': first_relation['allergen_name'],
                'symptom_name': first_relation['symptom_name'],
                'relation': first_relation['relation']
            }
        
        return {
            'id': str(x.id),
            'source': x.source,
            'title': x.title,
            'pmid': x.pmid,
            'publishDate': x.publish_date.isoformat() if x.publish_date else None,
            'authors': x.authors,
            'abstract': x.abstract,
            'keywords': x.keywords,
            'link': x.link,
            'entityRelation': entity_relation,
            'entityRelations': literature_entity_relations,  # 返回所有实体关系的数组
            'state': x.state,
            'literatureType': x.literature_type or 'epidemiology',  # 返回文献类型，默认为流行病学
            'traecScore': 0.0,  # 暂时设为0，后续可以根据评分算法计算
            'createdAt': x.created_at.isoformat() if x.created_at else None,
            'updatedAt': x.updated_at.isoformat() if x.updated_at else None,
        }
    
    return jsonify([to_dict(x) for x in items])


def _to_json_text(value):
    if value is None:
        return None
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False)
    # str or number
    return str(value)


def _parse_datetime(value):
    if not value:
        return None
    try:
        # common formats including 'YYYY-MM-DD HH:mm[:ss]'
        if isinstance(value, str):
            v = value.strip()
            # full datetime
            for fmt in [
                '%Y-%m-%d %H:%M:%S',
                '%Y-%m-%d %H:%M',
                '%Y/%m/%d %H:%M:%S',
                '%Y/%m/%d %H:%M',
            ]:
                try:
                    return datetime.strptime(v, fmt)
                except ValueError:
                    pass
            # date only
            if len(v) == 10 and v[4] == '-' and v[7] == '-':
                return datetime.fromisoformat(v + ' 00:00:00')
            if len(v) == 7 and v[4] == '-':
                return datetime.fromisoformat(v + '-01 00:00:00')
            if len(v) == 4 and v.isdigit():
                return datetime.fromisoformat(v + '-01-01 00:00:00')
            # common: YYYY/MM/DD
            if '/' in v:
                parts = v.split('/')
                if len(parts) == 3:
                    y, m, d = parts
                    return datetime(int(y), int(m), int(d), 0, 0, 0)
                if len(parts) == 2:
                    y, m = parts
                    return datetime(int(y), int(m), 1, 0, 0, 0)
        # if numeric like 20200101
        if isinstance(value, int):
            s = str(value)
            if len(s) == 8:
                return datetime(int(s[0:4]), int(s[4:6]), int(s[6:8]), 0, 0, 0)
    except Exception:
        return None
    return None


def _gen_external_id(source: str, item: dict) -> str:
    ext = (item.get('externalId') or '').strip() if isinstance(item.get('externalId'), str) else item.get('externalId')
    if ext:
        return str(ext)
    base = item.get('link') or (str(item.get('title') or '') + '|' + str(item.get('publishDate') or ''))
    raw = f"{source}|{base}"
    return hashlib.sha1(raw.encode('utf-8')).hexdigest()


def _normalize_keyword(kw: str) -> str:
    if kw is None:
        return ''
    s = str(kw).strip()
    if not s:
        return ''
    return s.lower()


def _split_people_or_keywords(val):
    if val is None:
        return None
    if isinstance(val, list):
        return [x for x in [str(v).strip() for v in val] if x]
    s = str(val)
    # 支持多种分隔符，包括中文 '、' 与 '；'，以及 ';;'
    for sep in [';;', '、', ';', '；', ',', '，', '|', ' ']:
        s = s.replace(sep, '\u0001')
    parts = [p.strip() for p in s.split('\u0001') if p.strip()]
    return parts or None



def _to_authors_json(val):
    arr = _split_people_or_keywords(val)
    return _to_json_text(arr)



@bp.post('/')
def create_literature_batch():
    body = request.get_json(silent=True) or {}
    items = body.get('items') or []
    if not isinstance(items, list) or len(items) == 0:
        return jsonify({'code': 'BadRequest', 'message': 'items must be a non-empty list'}), 400

    created, updated = 0, 0
    ids = []
    try:
        for raw in items:
            source = (raw.get('source') or '').strip().lower()
            if not source:
                return jsonify({'code': 'BadRequest', 'message': 'source is required for each item'}), 400
            ext_id = _gen_external_id(source, raw)

            title = (raw.get('title') or '').strip()
            if not title:
                return jsonify({'code': 'BadRequest', 'message': 'title is required for each item'}), 400

            authors = _to_authors_json(raw.get('authors'))
            abstract = raw.get('abstract')
            keywords = _to_json_text(raw.get('keywords'))
            link = raw.get('link')
            _dt = _parse_datetime(raw.get('publishDate'))
            pdate = _dt.date() if isinstance(_dt, datetime) else None

            obj = Literature.query.filter_by(source=source, external_id=ext_id).first()
            if obj:
                obj.title = title
                obj.authors = authors
                obj.publish_date = pdate
                obj.abstract = abstract
                obj.keywords = keywords
                obj.link = link
                updated += 1
            else:
                obj = Literature(
                    source=source,
                    external_id=ext_id,
                    title=title,
                    authors=authors,
                    publish_date=pdate,
                    abstract=abstract,
                    keywords=keywords,
                    link=link,
                )
                db.session.add(obj)
                created += 1
            db.session.flush()
            ids.append(str(obj.id))

        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({'code': 'Conflict', 'message': 'unique constraint violated'}), 409

    return jsonify({'created': created, 'updated': updated, 'ids': ids})


@bp.put('/<int:lit_id>')
def update_literature(lit_id: int):
    """更新文献信息、实体关系和评分数据"""
    
    # 获取文献记录
    literature = Literature.query.get(lit_id)
    if not literature:
        return jsonify({'code': 'NotFound', 'message': 'Literature not found'}), 404
    
    body = request.get_json(silent=True) or {}
    
    try:
        # 更新基本信息
        basic_info = body.get('basicInfo', {})
        entity_relations = body.get('entityRelations', [])
        
        if basic_info:
            if 'title' in basic_info:
                literature.title = basic_info['title']
            if 'source' in basic_info:
                literature.source = basic_info['source']
            if 'pmid' in basic_info:
                literature.pmid = basic_info['pmid']
            if 'authors' in basic_info:
                literature.authors = basic_info['authors']
            if 'publishDate' in basic_info:
                pub_date = basic_info['publishDate']
                if pub_date:
                    try:
                        literature.publish_date = datetime.fromisoformat(pub_date).date()
                    except ValueError:
                        pass
            if 'abstract' in basic_info:
                literature.abstract = basic_info['abstract']
            if 'link' in basic_info:
                literature.link = basic_info['link']
            # 从基本信息中获取文献类型
            if 'literatureType' in basic_info:
                literature.literature_type = basic_info['literatureType']
        
        # 1. 获取旧的实体关系
        old_sources = AllergenSymptomSource.query.filter_by(literature_id=lit_id).all()
        old_relations = {}  # 保存旧关系的映射 (allergen_id, symptom_id) -> (allergen_symptom_id, source_id)
        for src in old_sources:
            allergen_symptom = AllergenSymptom.query.get(src.allergen_symptom_id)
            if allergen_symptom:
                old_relations[(allergen_symptom.allergen_id, allergen_symptom.symptom_id)] = (allergen_symptom.id, src.id)
        
        
        # 2. 收集新的实体关系
        new_relations = {}  # 保存新关系的映射 (allergen_id, symptom_id) -> scoring_data
        for relation_data in entity_relations:
            allergen_id = relation_data.get('allergenId')
            symptom_id = relation_data.get('symptomId')
            scoring_data = relation_data.get('scoringData', {})
            
            if allergen_id and symptom_id:
                new_relations[(allergen_id, symptom_id)] = scoring_data
        
        
        # 3. 识别需要删除、添加和保持的关系
        old_relation_keys = set(old_relations.keys())
        new_relation_keys = set(new_relations.keys())
        
        relations_to_delete = old_relation_keys - new_relation_keys  # 需要删除的关系
        relations_to_add = new_relation_keys - old_relation_keys     # 需要添加的关系
        relations_to_keep = old_relation_keys & new_relation_keys    # 需要保持的关系
        
        
        updated_relations = []
        has_scoring = False
        
        # 4. 处理需要删除的关系
        for (allergen_id, symptom_id) in relations_to_delete:
            allergen_symptom_id, source_id = old_relations[(allergen_id, symptom_id)]
            
            # 删除佐证关联
            source = AllergenSymptomSource.query.get(source_id)
            if source:
                db.session.delete(source)
            
            # 删除对应的评分数据
            if literature.literature_type == 'epidemiology':
                scoring = LiteratureEpiScoring.query.filter_by(
                    literature_id=literature.id,
                    relation_id=allergen_symptom_id
                ).first()
                if scoring:
                    db.session.delete(scoring)
                    print(f'[Literature Update] 删除流行病学评分: relation_id={allergen_symptom_id}')
                else:
                    print(f'[Literature Update] 删除流行病学评分: relation_id={allergen_symptom_id}失败')
            elif literature.literature_type == 'in-vivo':
                scoring = LiteratureVivoScoring.query.filter_by(
                    literature_id=literature.id,
                    relation_id=allergen_symptom_id
                ).first()
                if scoring:
                    db.session.delete(scoring)
                    print(f'[Literature Update] 删除体内实验评分: relation_id={allergen_symptom_id}')
                else:
                    print(f'[Literature Update] 删除体内实验分: relation_id={allergen_symptom_id}失败')
            elif literature.literature_type == 'in-vitro':
                scoring = LiteratureVitroScoring.query.filter_by(
                    literature_id=literature.id,
                    relation_id=allergen_symptom_id
                ).first()
                if scoring:
                    db.session.delete(scoring)
                    print(f'[Literature Update] 删除体外实验评分: relation_id={allergen_symptom_id}')
                else:
                    print(f'[Literature Update] 删除体内实验评分: relation_id={allergen_symptom_id}失败')
        
        db.session.flush()
        
        # 5. 处理需要添加的关系
        for (allergen_id, symptom_id) in relations_to_add:
            scoring_data = new_relations[(allergen_id, symptom_id)]
            print(f'[Literature Update] 添加新关系: allergen_id={allergen_id}, symptom_id={symptom_id}')
            
            # 验证化学应激源-症状关系是否存在
            allergen_symptom = AllergenSymptom.query.filter_by(
                allergen_id=allergen_id,
                symptom_id=symptom_id
            ).first()
            
            is_new_relation = False
            
            # 如果关系不存在，创建新关系
            if not allergen_symptom:
                print(f'[Literature Update] AllergenSymptom关系不存在，创建新关系')
                allergen_symptom = AllergenSymptom(
                    allergen_id=allergen_id,
                    symptom_id=symptom_id
                )
                db.session.add(allergen_symptom)
                db.session.flush()
                is_new_relation = True
                
                # 重新查询以确保获取正确的关系ID
                allergen_symptom = AllergenSymptom.query.filter_by(
                    allergen_id=allergen_id,
                    symptom_id=symptom_id
                ).first()
                
                print(f'[Literature Update] 新AllergenSymptom已创建，ID: {allergen_symptom.id}')
            
            # 如果是新创建的关系，同步到Neo4j
            if is_new_relation:
                try:
                    from ..services.neo4j_sync import Neo4jSyncService
                    Neo4jSyncService.sync_allergen_symptom_relation(
                        allergen_id=allergen_id,
                        symptom_id=symptom_id,
                        relation_id=allergen_symptom.id,
                        operation='create'
                    )
                    print(f'[Literature Update] 关系已同步到Neo4j')
                except Exception as e:
                    print(f'[Literature Update] Neo4j同步失败: {e}')
            
            # 创建文献佐证关联
            literature_source = AllergenSymptomSource(
                allergen_symptom_id=allergen_symptom.id,
                literature_id=literature.id,
                evidence_strength=1.0
            )
            db.session.add(literature_source)
            db.session.flush()
            
            # 保存评分数据
            if scoring_data and scoring_data.get('concentrationWeight'):
                if literature.literature_type == 'epidemiology':
                    _save_epidemiology_scoring(literature.id, allergen_symptom.id, scoring_data)
                elif literature.literature_type == 'in-vivo':
                    _save_in_vivo_scoring(literature.id, allergen_symptom.id, scoring_data)
                elif literature.literature_type == 'in-vitro':
                    _save_in_vitro_scoring(literature.id, allergen_symptom.id, scoring_data)
                has_scoring = True
            
            updated_relations.append({
                'allergen_symptom_id': allergen_symptom.id,
                'literature_source_id': literature_source.id
            })
        
        # 6. 处理需要保持的关系（只更新评分数据）
        for (allergen_id, symptom_id) in relations_to_keep:
            allergen_symptom_id, source_id = old_relations[(allergen_id, symptom_id)]
            scoring_data = new_relations[(allergen_id, symptom_id)]
            print(f'[Literature Update] 保持关系: allergen_id={allergen_id}, symptom_id={symptom_id}')
            
            # 只更新评分数据，不删除和重建佐证
            if scoring_data and scoring_data.get('concentrationWeight'):
                if literature.literature_type == 'epidemiology':
                    _save_epidemiology_scoring(literature.id, allergen_symptom_id, scoring_data)
                elif literature.literature_type == 'in-vivo':
                    _save_in_vivo_scoring(literature.id, allergen_symptom_id, scoring_data)
                elif literature.literature_type == 'in-vitro':
                    _save_in_vitro_scoring(literature.id, allergen_symptom_id, scoring_data)
                has_scoring = True
            
            updated_relations.append({
                'allergen_symptom_id': allergen_symptom_id,
                'literature_source_id': source_id
            })
        
        db.session.flush()
        
        # 8. 更新文献状态
        literature.state = has_scoring
        
        db.session.commit()
        print(f'[Literature Update] 文献更新成功，共更新 {len(updated_relations)} 个关系')
        
        return jsonify({
            'success': True,
            'message': '文献更新成功',
            'data': {
                'id': literature.id,
                'relations_count': len(updated_relations)
            }
        })
        
    except Exception as e:
        db.session.rollback()
        print(f'[Literature Update] 更新失败: {str(e)}')
        return jsonify({'code': 'InternalError', 'message': str(e)}), 500


from ..services.traec_scoring import (
    recalculate_epi_concentration_weights as _recalculate_epi_concentration_weights,
    recalculate_vivo_concentration_weights as _recalculate_vivo_concentration_weights,
)


def _save_epidemiology_scoring(literature_id, relation_id, scoring_data):
    """保存流行病学研究评分数据"""
    # 查找或创建评分记录（按 literature_id 和 relation_id 联合查询）
    scoring = LiteratureEpiScoring.query.filter_by(
        literature_id=literature_id,
        relation_id=relation_id
    ).first()
    if not scoring:
        scoring = LiteratureEpiScoring(literature_id=literature_id, relation_id=relation_id)
        db.session.add(scoring)
    
    # 更新浓度权重数据
    concentration_weight = scoring_data.get('concentrationWeight', {})
    if concentration_weight:
        # 处理枚举字段，空字符串转为None
        mode_of_exposure = concentration_weight.get('modeOfExposure')
        scoring.mode_of_exposure = mode_of_exposure if mode_of_exposure and mode_of_exposure.strip() else None
        
        type_of_biosample = concentration_weight.get('typeOfBiosample')
        scoring.type_of_biosample = type_of_biosample if type_of_biosample and type_of_biosample.strip() else None
        
        scoring.concentrations = _safe_decimal(concentration_weight.get('concentrations'))
        scoring.concentration_unit = concentration_weight.get('concentrationUnit', 'mg/L')
        scoring.conversion_factor = _safe_decimal(concentration_weight.get('conversionFactor'))
        # concentration_weight (ε_k) 由批量重算函数填充，此处不从前端读取
    
    # 更新可靠性得分数据
    reliability_scores = scoring_data.get('reliabilityScores', {})
    # 为所有问题设置默认值1，如果用户没有选择
    for i in range(1, 11):
        q_key = f'q{i}'
        if q_key in reliability_scores:
            q_data = reliability_scores[q_key]
            setattr(scoring, f'reliability_q{i}_score', str(q_data.get('score', '1')))
            setattr(scoring, f'reliability_q{i}_comment', q_data.get('comment'))
        else:
            # 如果没有提供数据，设置默认值1
            setattr(scoring, f'reliability_q{i}_score', '1')
            setattr(scoring, f'reliability_q{i}_comment', None)
    
    # 计算总分
    total_score = 0
    for i in range(1, 11):
        score_attr = getattr(scoring, f'reliability_q{i}_score')
        if score_attr:
            total_score += float(score_attr)
    scoring.reliability_total_score = total_score
    
    # 更新相关性和风险强度
    scoring.correlation_score = str(scoring_data.get('correlation', '1'))
    scoring.correlation_comment = scoring_data.get('correlationComment')
    scoring.risk_intensity_score = str(scoring_data.get('riskIntensity', '1'))
    scoring.risk_intensity_comment = scoring_data.get('riskIntensityComment')
    
    # 不再计算总评分，总评分将在关系管理中处理
    
    # flush 使记录对同一 session 可见，然后批量重算 ε_k
    db.session.flush()
    _recalculate_epi_concentration_weights(relation_id, db.session)  # noqa: already passing session
    
    print(f'[Epidemiology Scoring] 保存评分数据: 浓度权重={scoring.concentration_weight}, 可靠性={scoring.reliability_total_score}, 相关性={scoring.correlation_score}, 风险强度={scoring.risk_intensity_score}')


def _save_in_vivo_scoring(literature_id, relation_id, scoring_data):
    """保存体内实验评分数据"""
    # 查找或创建评分记录（按 literature_id 和 relation_id 联合查询）
    scoring = LiteratureVivoScoring.query.filter_by(
        literature_id=literature_id,
        relation_id=relation_id
    ).first()
    if not scoring:
        scoring = LiteratureVivoScoring(literature_id=literature_id, relation_id=relation_id)
        db.session.add(scoring)
    
    # 更新浓度权重数据
    concentration_weight = scoring_data.get('concentrationWeight', {})
    if concentration_weight:
        type_of_model = concentration_weight.get('typeOfModel')
        scoring.type_of_model = type_of_model if type_of_model and type_of_model.strip() else None
        
        # 处理枚举字段，空字符串转为None
        mode_of_exposure = concentration_weight.get('modeOfExposure')
        scoring.mode_of_exposure = mode_of_exposure if mode_of_exposure and mode_of_exposure.strip() else None
        
        scoring.dose = _safe_decimal(concentration_weight.get('dose'))
        
        # 处理剂量单位枚举字段
        dose_unit = concentration_weight.get('doseUnit', 'mg/kg/d')
        scoring.dose_unit = dose_unit if dose_unit and dose_unit.strip() else 'mg/kg/d'
        
        scoring.noael = _safe_decimal(concentration_weight.get('noael'))
        scoring.conversion_factors = _safe_decimal(concentration_weight.get('conversionFactor'))
        # concentration_weight (ε_k) 由批量重算函数填充，此处不从前端读取
    
    # 更新可靠性得分数据
    reliability_scores = scoring_data.get('reliabilityScores', {})
    # 为所有问题设置默认值1，如果用户没有选择
    for i in range(1, 11):
        q_key = f'q{i}'
        if q_key in reliability_scores:
            q_data = reliability_scores[q_key]
            setattr(scoring, f'reliability_q{i}_score', str(q_data.get('score', '1')))
            setattr(scoring, f'reliability_q{i}_comment', q_data.get('comment'))
        else:
            # 如果没有提供数据，设置默认值1
            setattr(scoring, f'reliability_q{i}_score', '1')
            setattr(scoring, f'reliability_q{i}_comment', None)
    
    # 计算总分
    total_score = 0
    for i in range(1, 11):
        score_attr = getattr(scoring, f'reliability_q{i}_score')
        if score_attr:
            total_score += float(score_attr)
    scoring.reliability_total_score = total_score
    
    # 更新相关性和风险强度
    scoring.correlation_score = str(scoring_data.get('correlation', '1'))
    scoring.correlation_comment = scoring_data.get('correlationComment')
    scoring.risk_intensity_score = str(scoring_data.get('riskIntensity', '1'))
    scoring.risk_intensity_comment = scoring_data.get('riskIntensityComment')
    
    # 不再计算总评分，总评分将在关系管理中处理
    
    # flush 使记录对同一 session 可见，然后批量重算 ε_k
    db.session.flush()
    _recalculate_vivo_concentration_weights(relation_id, db.session)
    
    print(f'[In-Vivo Scoring] 保存评分数据: 浓度权重={scoring.concentration_weight}, 可靠性={scoring.reliability_total_score}, 相关性={scoring.correlation_score}, 风险强度={scoring.risk_intensity_score}')


def _save_in_vitro_scoring(literature_id, relation_id, scoring_data):
    """保存体外实验评分数据"""
    # 查找或创建评分记录（按 literature_id 和 relation_id 联合查询）
    scoring = LiteratureVitroScoring.query.filter_by(
        literature_id=literature_id,
        relation_id=relation_id
    ).first()
    if not scoring:
        scoring = LiteratureVitroScoring(literature_id=literature_id, relation_id=relation_id)
        db.session.add(scoring)
    
    # 更新浓度权重数据
    concentration_weight = scoring_data.get('concentrationWeight', {})
    if concentration_weight:
        scoring.dose = _safe_decimal(concentration_weight.get('dose'))
        
        # 处理剂量单位字段
        dose_unit = concentration_weight.get('doseUnit', 'mM')
        scoring.dose_unit = dose_unit if dose_unit and dose_unit.strip() else 'mM'
        
        scoring.molecular_weight = _safe_decimal(concentration_weight.get('molecularWeight'))
        scoring.concentration_weight = _safe_decimal(concentration_weight.get('score'))
    
    # 更新可靠性得分数据
    reliability_scores = scoring_data.get('reliabilityScores', {})
    # 为所有问题设置默认值1，如果用户没有选择
    for i in range(1, 11):
        q_key = f'q{i}'
        if q_key in reliability_scores:
            q_data = reliability_scores[q_key]
            setattr(scoring, f'reliability_q{i}_score', str(q_data.get('score', '1')))
            setattr(scoring, f'reliability_q{i}_comment', q_data.get('comment'))
        else:
            # 如果没有提供数据，设置默认值1
            setattr(scoring, f'reliability_q{i}_score', '1')
            setattr(scoring, f'reliability_q{i}_comment', None)
    
    # 计算总分
    total_score = 0
    for i in range(1, 11):
        score_attr = getattr(scoring, f'reliability_q{i}_score')
        if score_attr:
            total_score += float(score_attr)
    scoring.reliability_total_score = total_score
    
    # 更新相关性和风险强度
    scoring.correlation_score = str(scoring_data.get('correlation', '1'))
    scoring.correlation_comment = scoring_data.get('correlationComment')
    scoring.risk_intensity_score = str(scoring_data.get('riskIntensity', '1'))
    scoring.risk_intensity_comment = scoring_data.get('riskIntensityComment')
    
    # 不再计算总评分，总评分将在关系管理中处理
    
    print(f'[In-Vitro Scoring] 保存评分数据: 浓度权重={scoring.concentration_weight}, 可靠性={scoring.reliability_total_score}, 相关性={scoring.correlation_score}, 风险强度={scoring.risk_intensity_score}')


def _safe_decimal(value):
    """安全转换为Decimal类型"""
    if value is None or value == '':
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def _get_epidemiology_scoring_data(scoring):
    """将流行病学评分数据转换为前端格式"""
    return {
        'concentrationWeight': {
            'modeOfExposure': scoring.mode_of_exposure or '',
            'typeOfBiosample': scoring.type_of_biosample or '',
            'concentrations': str(scoring.concentrations) if scoring.concentrations else '',
            'concentrationUnit': scoring.concentration_unit or 'mg/L',
            'conversionFactor': str(scoring.conversion_factor) if scoring.conversion_factor else ''
        },
        'reliabilityScores': {
            'q1': {'score': str(scoring.reliability_q1_score) if scoring.reliability_q1_score is not None else '', 'comment': scoring.reliability_q1_comment or ''},
            'q2': {'score': str(scoring.reliability_q2_score) if scoring.reliability_q2_score is not None else '', 'comment': scoring.reliability_q2_comment or ''},
            'q3': {'score': str(scoring.reliability_q3_score) if scoring.reliability_q3_score is not None else '', 'comment': scoring.reliability_q3_comment or ''},
            'q4': {'score': str(scoring.reliability_q4_score) if scoring.reliability_q4_score is not None else '', 'comment': scoring.reliability_q4_comment or ''},
            'q5': {'score': str(scoring.reliability_q5_score) if scoring.reliability_q5_score is not None else '', 'comment': scoring.reliability_q5_comment or ''},
            'q6': {'score': str(scoring.reliability_q6_score) if scoring.reliability_q6_score is not None else '', 'comment': scoring.reliability_q6_comment or ''},
            'q7': {'score': str(scoring.reliability_q7_score) if scoring.reliability_q7_score is not None else '', 'comment': scoring.reliability_q7_comment or ''},
            'q8': {'score': str(scoring.reliability_q8_score) if scoring.reliability_q8_score is not None else '', 'comment': scoring.reliability_q8_comment or ''},
            'q9': {'score': str(scoring.reliability_q9_score) if scoring.reliability_q9_score is not None else '', 'comment': scoring.reliability_q9_comment or ''},
            'q10': {'score': str(scoring.reliability_q10_score) if scoring.reliability_q10_score is not None else '', 'comment': scoring.reliability_q10_comment or ''}
        },
        'correlation': str(scoring.correlation_score) if scoring.correlation_score is not None else '',
        'riskIntensity': str(scoring.risk_intensity_score) if scoring.risk_intensity_score is not None else ''
    }


def _get_in_vivo_scoring_data(scoring):
    """将体内实验评分数据转换为前端格式"""
    return {
        'concentrationWeight': {
            'modelType': scoring.type_of_model or '',
            'modeOfExposure': scoring.mode_of_exposure or '',
            'dose': str(scoring.dose) if scoring.dose else '',
            'doseUnit': scoring.dose_unit or 'mg/kg/d',
            'noael': str(scoring.noael) if scoring.noael else '',
            'conversionFactor': str(scoring.conversion_factors) if scoring.conversion_factors else ''
        },
        'reliabilityScores': {
            'q1': {'score': str(scoring.reliability_q1_score) if scoring.reliability_q1_score is not None else '', 'comment': scoring.reliability_q1_comment or ''},
            'q2': {'score': str(scoring.reliability_q2_score) if scoring.reliability_q2_score is not None else '', 'comment': scoring.reliability_q2_comment or ''},
            'q3': {'score': str(scoring.reliability_q3_score) if scoring.reliability_q3_score is not None else '', 'comment': scoring.reliability_q3_comment or ''},
            'q4': {'score': str(scoring.reliability_q4_score) if scoring.reliability_q4_score is not None else '', 'comment': scoring.reliability_q4_comment or ''},
            'q5': {'score': str(scoring.reliability_q5_score) if scoring.reliability_q5_score is not None else '', 'comment': scoring.reliability_q5_comment or ''},
            'q6': {'score': str(scoring.reliability_q6_score) if scoring.reliability_q6_score is not None else '', 'comment': scoring.reliability_q6_comment or ''},
            'q7': {'score': str(scoring.reliability_q7_score) if scoring.reliability_q7_score is not None else '', 'comment': scoring.reliability_q7_comment or ''},
            'q8': {'score': str(scoring.reliability_q8_score) if scoring.reliability_q8_score is not None else '', 'comment': scoring.reliability_q8_comment or ''},
            'q9': {'score': str(scoring.reliability_q9_score) if scoring.reliability_q9_score is not None else '', 'comment': scoring.reliability_q9_comment or ''},
            'q10': {'score': str(scoring.reliability_q10_score) if scoring.reliability_q10_score is not None else '', 'comment': scoring.reliability_q10_comment or ''}
        },
        'correlation': str(scoring.correlation_score) if scoring.correlation_score is not None else '',
        'riskIntensity': str(scoring.risk_intensity_score) if scoring.risk_intensity_score is not None else ''
    }


def _get_in_vitro_scoring_data(scoring):
    """将体外实验评分数据转换为前端格式"""
    return {
        'concentrationWeight': {
            'dose': str(scoring.dose) if scoring.dose else '',
            'doseUnit': scoring.dose_unit or 'μM',
            'molecularWeight': str(scoring.molecular_weight) if scoring.molecular_weight else ''
        },
        'reliabilityScores': {
            'q1': {'score': str(scoring.reliability_q1_score) if scoring.reliability_q1_score is not None else '', 'comment': scoring.reliability_q1_comment or ''},
            'q2': {'score': str(scoring.reliability_q2_score) if scoring.reliability_q2_score is not None else '', 'comment': scoring.reliability_q2_comment or ''},
            'q3': {'score': str(scoring.reliability_q3_score) if scoring.reliability_q3_score is not None else '', 'comment': scoring.reliability_q3_comment or ''},
            'q4': {'score': str(scoring.reliability_q4_score) if scoring.reliability_q4_score is not None else '', 'comment': scoring.reliability_q4_comment or ''},
            'q5': {'score': str(scoring.reliability_q5_score) if scoring.reliability_q5_score is not None else '', 'comment': scoring.reliability_q5_comment or ''},
            'q6': {'score': str(scoring.reliability_q6_score) if scoring.reliability_q6_score is not None else '', 'comment': scoring.reliability_q6_comment or ''},
            'q7': {'score': str(scoring.reliability_q7_score) if scoring.reliability_q7_score is not None else '', 'comment': scoring.reliability_q7_comment or ''},
            'q8': {'score': str(scoring.reliability_q8_score) if scoring.reliability_q8_score is not None else '', 'comment': scoring.reliability_q8_comment or ''},
            'q9': {'score': str(scoring.reliability_q9_score) if scoring.reliability_q9_score is not None else '', 'comment': scoring.reliability_q9_comment or ''},
            'q10': {'score': str(scoring.reliability_q10_score) if scoring.reliability_q10_score is not None else '', 'comment': scoring.reliability_q10_comment or ''}
        },
        'correlation': str(scoring.correlation_score) if scoring.correlation_score is not None else '',
        'riskIntensity': str(scoring.risk_intensity_score) if scoring.risk_intensity_score is not None else ''
    }


@bp.get('/<int:lit_id>/scoring')
def get_literature_scoring(lit_id: int):
    """获取文献的评分数据"""
    logger = logging.getLogger(__name__)
    
    literature = Literature.query.get(lit_id)
    if not literature:
        return jsonify({'code': 'NotFound', 'message': 'Literature not found'}), 404
    
    logger.info(f'[Get Scoring] 文献 {lit_id} 状态: {literature.state}')
    
    # 根据文献状态返回不同的数据
    if literature.state is False or literature.state is None:
        # 待处理状态：返回空的评分结构，供用户填写
        result = {
            'literatureId': lit_id,
            'status': 'pending',
            'epidemiology': None,
            'inVivo': None,
            'inVitro': None
        }
        logger.info(f'[Get Scoring] 返回待处理状态数据: {result}')
    else:
        # 已处理状态：返回已保存的评分数据
        epi_scoring = LiteratureEpiScoring.query.filter_by(literature_id=lit_id).first()
        vivo_scoring = LiteratureVivoScoring.query.filter_by(literature_id=lit_id).first()
        vitro_scoring = LiteratureVitroScoring.query.filter_by(literature_id=lit_id).first()
        
        logger.info(f'[Get Scoring] 查询结果 - 流行病学: {epi_scoring is not None}, 体内: {vivo_scoring is not None}, 体外: {vitro_scoring is not None}')
        
        result = {
            'literatureId': lit_id,
            'status': 'processed',
            'epidemiology': _format_epi_scoring(epi_scoring) if epi_scoring else None,
            'inVivo': _format_vivo_scoring(vivo_scoring) if vivo_scoring else None,
            'inVitro': _format_vitro_scoring(vitro_scoring) if vitro_scoring else None
        }
        logger.info(f'[Get Scoring] 返回已处理状态数据: {result}')
    
    return jsonify(result)


def _format_epi_scoring(scoring):
    """格式化流行病学评分数据"""
    if not scoring:
        return None
    
    reliability_scores = {}
    for i in range(1, 11):
        score_attr = getattr(scoring, f'reliability_q{i}_score')
        comment_attr = getattr(scoring, f'reliability_q{i}_comment')
        reliability_scores[f'q{i}'] = {
            'score': score_attr,
            'comment': comment_attr
        }
    
    return {
        'id': scoring.id,
        'concentrationWeight': {
            'modeOfExposure': scoring.mode_of_exposure,
            'typeOfBiosample': scoring.type_of_biosample,
            'concentrations': float(scoring.concentrations) if scoring.concentrations else None,
            'concentrationUnit': scoring.concentration_unit,
            'conversionFactor': float(scoring.conversion_factor) if scoring.conversion_factor else None,
            'score': float(scoring.concentration_weight) if scoring.concentration_weight else None
        },
        'reliabilityScores': reliability_scores,
        'reliabilityTotalScore': float(scoring.reliability_total_score) if scoring.reliability_total_score else None,
        'correlationScore': scoring.correlation_score,
        'correlationComment': scoring.correlation_comment,
        'riskIntensityScore': scoring.risk_intensity_score,
        'riskIntensityComment': scoring.risk_intensity_comment,
    }


def _format_vivo_scoring(scoring):
    """格式化体内实验评分数据"""
    if not scoring:
        return None
    
    reliability_scores = {}
    for i in range(1, 11):
        score_attr = getattr(scoring, f'reliability_q{i}_score')
        comment_attr = getattr(scoring, f'reliability_q{i}_comment')
        reliability_scores[f'q{i}'] = {
            'score': score_attr,
            'comment': comment_attr
        }
    
    return {
        'id': scoring.id,
        'concentrationWeight': {
            'typeOfModel': scoring.type_of_model,
            'modeOfExposure': scoring.mode_of_exposure,
            'dose': float(scoring.dose) if scoring.dose else None,
            'doseUnit': scoring.dose_unit,
            'noael': float(scoring.noael) if scoring.noael else None,
            'conversionFactors': float(scoring.conversion_factors) if scoring.conversion_factors else None,
            'score': float(scoring.concentration_weight) if scoring.concentration_weight else None
        },
        'reliabilityScores': reliability_scores,
        'reliabilityTotalScore': float(scoring.reliability_total_score) if scoring.reliability_total_score else None,
        'correlationScore': scoring.correlation_score,
        'correlationComment': scoring.correlation_comment,
        'riskIntensityScore': scoring.risk_intensity_score,
        'riskIntensityComment': scoring.risk_intensity_comment,
    }


def _format_vitro_scoring(scoring):
    """格式化体外实验评分数据"""
    if not scoring:
        return None
    
    reliability_scores = {}
    for i in range(1, 11):
        score_attr = getattr(scoring, f'reliability_q{i}_score')
        comment_attr = getattr(scoring, f'reliability_q{i}_comment')
        reliability_scores[f'q{i}'] = {
            'score': score_attr,
            'comment': comment_attr
        }
    
    return {
        'id': scoring.id,
        'concentrationWeight': {
            'dose': float(scoring.dose) if scoring.dose else None,
            'doseUnit': scoring.dose_unit,
            'molecularWeight': float(scoring.molecular_weight) if scoring.molecular_weight else None,
            'score': float(scoring.concentration_weight) if scoring.concentration_weight else None
        },
        'reliabilityScores': reliability_scores,
        'reliabilityTotalScore': float(scoring.reliability_total_score) if scoring.reliability_total_score else None,
        'correlationScore': scoring.correlation_score,
        'correlationComment': scoring.correlation_comment,
        'riskIntensityScore': scoring.risk_intensity_score,
        'riskIntensityComment': scoring.risk_intensity_comment,
    }


@bp.delete('/<int:lit_id>')
def delete_literature(lit_id: int):
    """删除文献记录"""
    logger = logging.getLogger(__name__)
    
    try:
        # 查找文献记录
        literature = db.session.get(Literature, lit_id)
        if not literature:
            return jsonify({
                'code': 404,
                'message': '文献不存在'
            }), 404
        
        # 删除相关的评分数据（根据文献类型）
        
        # 删除流行病学评分数据
        epi_count = LiteratureEpiScoring.query.filter_by(literature_id=lit_id).delete()
        if epi_count > 0:
            logger.info(f'删除了 {epi_count} 条流行病学评分记录')
        
        # 删除体内实验评分数据
        vivo_count = LiteratureVivoScoring.query.filter_by(literature_id=lit_id).delete()
        if vivo_count > 0:
            logger.info(f'删除了 {vivo_count} 条体内实验评分记录')
        
        # 删除体外实验评分数据
        vitro_count = LiteratureVitroScoring.query.filter_by(literature_id=lit_id).delete()
        if vitro_count > 0:
            logger.info(f'删除了 {vitro_count} 条体外实验评分记录')
        
        # 删除关联关系
        relation_count = AllergenSymptomSource.query.filter_by(literature_id=lit_id).delete()
        if relation_count > 0:
            logger.info(f'删除了 {relation_count} 条文献关联关系')
        
        # 最后删除文献记录
        db.session.delete(literature)
        db.session.commit()
        
        logger.info(f'[Literature Delete] 成功删除文献 ID: {lit_id}')
        return jsonify({
            'code': 200,
            'message': '文献删除成功'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f'[Literature Delete] 删除文献失败: {e}')
        return jsonify({
            'code': 500,
            'message': f'删除失败: {str(e)}'
        }), 500


@bp.delete('/filter/<int:lit_id>')
def delete_literature_filter(lit_id: int):
    """删除文献筛选记录"""
    logger = logging.getLogger(__name__)
    logger.info(f'[Literature Filter Delete] 尝试删除文献筛选记录 ID: {lit_id}')
    
    try:
        # 查找记录
        x = LiteratureFilter.query.get(lit_id)
        if not x:
            logger.warning(f'[Literature Filter Delete] 未找到文献筛选记录 ID: {lit_id}')
            return jsonify({'code': 'NotFound', 'message': 'literature not found'}), 404
        
        logger.info(f'[Literature Filter Delete] 找到记录: {x.title[:50]}...')
        
        # 删除文献记录
        db.session.delete(x)
        db.session.commit()
        
        logger.info(f'[Literature Filter Delete] 成功删除文献筛选记录 ID: {lit_id}')
        return jsonify({'success': True, 'message': '删除成功'})
        
    except IntegrityError as e:
        db.session.rollback()
        logger.error(f'[Literature Filter Delete] 数据库完整性错误: {e}')
        return jsonify({
            'code': 'IntegrityError', 
            'message': '删除失败：存在关联数据，无法删除',
            'detail': str(e)
        }), 409
        
    except Exception as e:
        db.session.rollback()
        logger.error(f'[Literature Filter Delete] 删除失败: {e}', exc_info=True)
        return jsonify({
            'code': 'DeleteError', 
            'message': '删除失败',
            'detail': str(e)
        }), 500


def _call_crawler(site: str, keyword: str, progress_cb=None):
    logger = logging.getLogger(__name__)
    
    try:
        if site == 'pubmed':
            # PubMed 使用英文检索：将关键词翻译为英文后再查询
            try:
                en_kw = translate_to_en([keyword])[0] if keyword else keyword
                # 检查翻译是否成功（如果翻译结果和原文相同，说明翻译失败）
                if en_kw == keyword and _is_chinese(keyword):
                    logger.warning(f'[Crawler] PubMed 关键词翻译失败，跳过PubMed爬取: {keyword}')
                    return []
                logger.info(f'[Crawler] PubMed 关键词翻译: {keyword} -> {en_kw}')
            except Exception as e:
                logger.warning(f'[Crawler] PubMed 关键词翻译失败，跳过PubMed爬取: {e}')
                return []
            if pubmed_crawler:
                result = pubmed_crawler(en_kw, pages=2, progress=progress_cb) or []
            else:
                result = []
            logger.info(f'[Crawler] PubMed 爬虫返回 {len(result)} 条结果')
            return result
    except Exception as e:
        logger.error(f'[Crawler] 爬虫异常: {e}', exc_info=True)
        return []
    logger.warning(f'[Crawler] 未知站点: {site}')
    return []


def _is_chinese(text: str) -> bool:
    """判断文本是否包含中文字符"""
    return bool(re.search(r'[\u4e00-\u9fff]', text))


@bp.get('/filter')
def list_literature_filter():
    """列出暂存在 literature_filter 的采集结果。
    支持按 search_keyword 查询匹配的文献。
    """
    logger = logging.getLogger(__name__)
    
    page = int(request.args.get('page', 1) or 1)
    page_size = int(request.args.get('pageSize', 100) or 100)
    page_size = max(1, min(200, page_size))
    search_keyword = request.args.get('searchKeyword')

    logger.info(f'[Literature Filter] 查询参数 - page: {page}, pageSize: {page_size}, searchKeyword: {search_keyword}')

    q = LiteratureFilter.query
    
    # 如果提供了搜索关键词，按关键词筛选（支持模糊匹配）
    if search_keyword:
        # 使用 LIKE 进行模糊匹配，这样可以匹配包含该关键词的文献
        q = q.filter(LiteratureFilter.search_keyword.like(f'%{search_keyword}%'))
        logger.info(f'[Literature Filter] 应用搜索关键词过滤: %{search_keyword}%')
    
    q = q.order_by(LiteratureFilter.id.desc())
    total = q.count()
    logger.info(f'[Literature Filter] 查询结果总数: {total}')
    
    items = q.offset((page - 1) * page_size).limit(page_size).all()
    logger.info(f'[Literature Filter] 返回 {len(items)} 条记录')
    

    def to_dict(x: LiteratureFilter):
        return {
            'id': str(x.id),
            'source': x.source,
            'title': x.title,
            'authors': x.authors,
            'publishDate': x.publish_date.isoformat() if x.publish_date else None,
            'literatureType': x.literature_type,
            'searchKeyword': x.search_keyword,
            'link': x.link,
        }

    # 如果查询结果为空，记录前5条数据的 search_keyword 用于调试
    if total == 0 and search_keyword:
        sample_items = LiteratureFilter.query.order_by(LiteratureFilter.id.desc()).limit(5).all()
        sample_keywords = [item.search_keyword for item in sample_items]
        logger.warning(f'[Literature Filter] 未找到匹配结果。数据库中最近5条记录的search_keyword: {sample_keywords}')
    
    return jsonify({'items': [to_dict(x) for x in items], 'page': page, 'pageSize': page_size, 'total': total})


@bp.post('/crawl')
def crawl_and_ingest():
    logger = logging.getLogger(__name__)
    
    body = request.get_json(silent=True) or {}
    logger.info(f'[Literature Crawl] 收到爬取请求: {body}')
    
    product_id = body.get('productId')
    product_name = body.get('productName')
    allergen_id = body.get('allergenId')
    # 文献采集使用 PubMed
    sites = ['pubmed']
    keywords_override = body.get('keywordsOverride')
    min_per_kw = int(body.get('minPerKeyword') or 5)

    pid = None
    aid = None
    
    # 优先使用过敏原ID
    if allergen_id is not None:
        try:
            aid = int(allergen_id)
        except (TypeError, ValueError):
            aid = None
    # 如果没有过敏原ID，尝试产品ID
    elif product_id is not None:
        try:
            pid = int(product_id)
        except (TypeError, ValueError):
            pid = None
    elif product_name:
        p = Product.query.filter_by(name=str(product_name)).first()
        pid = p.id if p else None

    # K 集合：优先使用 keywordsOverride，否则根据 allergen/product 获取
    if keywords_override and isinstance(keywords_override, list):
        raw_k = [str(x) for x in keywords_override]
        logger.info(f'[Literature Crawl] 使用覆盖关键词: {raw_k}')
    elif aid:
        # 过敏原模式：使用过敏原名称作为关键词
        allergen = Allergen.query.get(aid)
        raw_k = [allergen.name] if allergen else []
        logger.info(f'[Literature Crawl] 使用过敏原关键词: {raw_k}')
    elif pid:
        # 产品模式：简化版，使用产品名称作为关键词
        p = Product.query.get(pid)
        raw_k = [p.name] if p else []
        logger.info(f'[Literature Crawl] 使用产品关键词: {raw_k}')
    else:
        # 既没有 keywordsOverride，也没有 allergen/product
        logger.warning('[Literature Crawl] 缺少必需参数')
        return jsonify({'code': 'BadRequest', 'message': 'keywordsOverride or allergen/product is required'}), 400
    
    K = sorted(set([_normalize_keyword(k) for k in raw_k if _normalize_keyword(k)]))
    
    # 如果没有关键词，直接返回
    if not K:
        logger.warning('[Literature Crawl] 没有有效关键词')
        return jsonify({'code': 'BadRequest', 'message': 'No keywords available for crawling'}), 400

    logger.info(f'[Literature Crawl] 最终关键词列表: {K}')
    
    # 简化版：直接爬取所有关键词，不检查本地数量
    targets = K

    summary = {s: {"requested": 0, "crawled": 0, "savedToFilter": 0} for s in sites}
    by_kw = []

    def emit(msg: str):
        # 轻量进度输出：控制台日志 + 可选扩展为 WebSocket/SSE
        logger.info(f'[Crawler] {msg}')
        print(msg)

    try:
        for kw in targets:
            logger.info(f'[Literature Crawl] 开始处理关键词: {kw}')
            kw_created = 0
            kw_updated = 0
            kw_bound = 0
            for site in sites:
                summary[site]["requested"] += 1
                logger.info(f'[Literature Crawl] 调用 {site} 爬虫，关键词: {kw}')
                # 调用爬虫，直接返回列表，并透传进度回调
                try:
                    data = _call_crawler(site, kw, emit)
                    logger.info(f'[Literature Crawl] {site} 爬虫返回 {len(data or [])} 条数据')
                except Exception as e:
                    logger.error(f'[Literature Crawl] {site} 爬虫调用失败: {e}', exc_info=True)
                    data = []
                summary[site]["crawled"] += len(data or [])
                for item in (data or []):
                    # 构造成 ingest item - PubMed
                    mapped = {
                        'source': 'pubmed',
                        'title': item.get('title') or '',
                        'authors': item.get('author'),
                        'publishDate': item.get('date'),
                        'abstract': None,  # 不保存摘要
                        'keywords': None,  # 不保存关键词
                        'link': item.get('link'),
                        'rawPayload': item,
                    }
                    # 论文自带关键词显示存储在 keywords；用于绑定的关键词通过 bindWith 传入
                    mapped['bindWith'] = [kw]

                    # 改为写入 literature_filter 暂存表
                    try:
                        _dt = _parse_datetime(mapped.get('publishDate'))
                        lf = LiteratureFilter(
                            source=mapped.get('source') or '',
                            title=mapped.get('title') or '',
                            pmid=mapped.get('pmid') or '',
                            authors=_to_authors_json(mapped.get('authors')),
                            publish_date=_dt.date() if isinstance(_dt, datetime) else None,
                            literature_type=mapped.get('literature_type') or 'epidemiology',
                            abstract=mapped.get('abstract'),
                            keywords=mapped.get('keywords'),
                            search_keyword=kw,  # 保存搜索关键词
                            link=mapped.get('link'),
                        )
                        db.session.add(lf)
                        db.session.flush()
                        summary[site]['savedToFilter'] += 1
                        logger.info(f'[Literature Crawl] 保存文献到filter: {mapped.get("title")[:50]}...')
                    except Exception as e:
                        logger.error(f'[Literature Crawl] 保存失败: {e}')
                        pass
            by_kw.append({"keyword": kw, "created": kw_created, "updated": kw_updated, "bound": kw_bound})

        db.session.commit()
        logger.info(f'[Literature Crawl] 爬取完成，统计: {summary}')
    except IntegrityError as e:
        db.session.rollback()
        logger.error(f'[Literature Crawl] 数据库冲突: {e}')
        return jsonify({'code': 'Conflict', 'message': 'unique constraint violated'}), 409
    except Exception as e:
        db.session.rollback()
        logger.error(f'[Literature Crawl] 未知错误: {e}', exc_info=True)
        return jsonify({'code': 'InternalError', 'message': str(e)}), 500

    logger.info(f'[Literature Crawl] 返回结果: summary={summary}, byKeyword={by_kw}')
    return jsonify({'summary': summary, 'byKeyword': by_kw})


@bp.post('/filter/promote/<int:filter_id>')
def promote_filter_item(filter_id: int):
    """将 literature_filter 中的单条记录转存到 literature 表，用于信息管理后续使用。"""
    x = LiteratureFilter.query.get(filter_id)
    if not x:
        return jsonify({'code': 'NotFound', 'message': 'filter item not found'}), 404

    try:
        # 简单按标题去重：若已存在则跳过创建
        existed = Literature.query.filter_by(title=x.title).first()
        if existed is None:
            obj = Literature(
                source=x.source,
                title=x.title,
                authors=x.authors,
                publish_date=x.publish_date,
                literature_type=x.literature_type,
                abstract=x.abstract,  # 从 LiteratureFilter 获取摘要
                keywords=x.keywords,  # 从 LiteratureFilter 获取关键词
                link=x.link,
            )
            db.session.add(obj)
            db.session.flush()
        # 移除 filter 项
        db.session.delete(x)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({'code': 'Conflict', 'message': 'promote failed due to conflict'}), 409

    return jsonify({'success': True})


@bp.post('/enhanced-crawl')
def enhanced_crawl():
    """
    增强的文献采集接口
    使用增强的PubMed爬虫和百度翻译
    支持：化学应急源 + 不良反应 + 研究类型筛选
    """
    
    body = request.get_json(silent=True) or {}
    print(f'[Enhanced Literature Crawl] 收到爬取请求: {body}')
    
    # 获取参数
    chemical_source = body.get('chemicalSource', '').strip()
    adverse_reaction = body.get('adverseReaction', '').strip()
    study_type = body.get('studyType', '').strip() or None
    
    # 验证必需参数
    if not chemical_source or not adverse_reaction:
        print('[Enhanced Literature Crawl] 缺少必需参数')
        return jsonify({'code': 'BadRequest', 'message': '化学应急源和不良反应为必填项'}), 400
    
    try:
        # 初始化百度翻译服务
        if not BaiduTranslationService:
            return jsonify({
                'success': False,
                'message': '百度翻译服务不可用'
            }), 500
        translator = BaiduTranslationService()
        
        # 导入PubMed API爬虫（使用官方API，避免403错误）
        if not pubmed_api_crawler:
            return jsonify({
                'success': False,
                'message': 'PubMed API爬虫不可用'
            }), 500
        
        # 翻译化学应急源和不良反应为英文（用于PubMed搜索）
        chemical_source_en = translator.translate_batch([chemical_source], 'auto', 'en')[0]
        adverse_reaction_en = translator.translate_batch([adverse_reaction], 'auto', 'en')[0]
        
        # 调用PubMed API爬虫（使用英文关键词）
        results = pubmed_api_crawler(
            chemical_source=chemical_source_en,
            adverse_reaction=adverse_reaction_en,
            study_type=study_type,
            translator=translator,
            max_results=100,  # 最多获取100条
            start_year=2000,  # 从2000年开始
            end_year=datetime.now().year
        )
        
        # AI 分类：对爬取结果进行研究类型判定
        ai_classified = 0
        classifier = None
        if LiteratureClassifier:
            try:
                classifier = LiteratureClassifier()
                classify_results = classifier.classify_batch(results)
                ai_classified = len(classify_results)
            except Exception as e:
                print(f'[Enhanced Literature Crawl] AI分类初始化失败: {e}')
                classify_results = [None] * len(results)
        else:
            classify_results = [None] * len(results)
        
        # 保存到 literature_filter 表
        saved_count = 0
        for i, item in enumerate(results):
            try:
                # 构建搜索关键词
                search_keyword = f"{chemical_source}-{adverse_reaction}"
                if study_type:
                    search_keyword += f"-{study_type}"
                
                # 解析日期
                _dt = _parse_datetime(item.get('date'))
                
                # 获取 AI 分类结果
                ai_result = classify_results[i] if i < len(classify_results) else None
                if ai_result and ai_result.get('study_type'):
                    literature_type = ai_result['study_type']
                else:
                    literature_type = item.get('literature_type') or 'other'
                
                # 创建 LiteratureFilter 记录
                lf = LiteratureFilter(
                    source='pubmed',
                    title=item.get('title_zh') or item.get('title') or '',
                    pmid=item.get('pmid') or '',
                    authors=_to_authors_json(item.get('author')),
                    publish_date=_dt.date() if isinstance(_dt, datetime) else None,
                    literature_type=literature_type,
                    search_keyword=search_keyword,
                    abstract=item.get('abstract_zh') or item.get('abstract'),
                    keywords=item.get('keywords'),
                    link=item.get('link'),
                )
                db.session.add(lf)
                db.session.flush()
                saved_count += 1
                
            except Exception as e:
                print(f'[Enhanced Literature Crawl] 保存文献失败: {e}')
                continue
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'crawled': len(results),
            'saved': saved_count,
            'ai_classified': ai_classified,
            'message': f'成功爬取并保存 {saved_count} 条文献，AI分类 {ai_classified} 条'
        })
        
    except Exception as e:
        db.session.rollback()
        print(f'[Enhanced Literature Crawl] 爬取失败: {e}')
        return jsonify({'code': 'InternalError', 'message': str(e)}), 500


@bp.post('/work-crawl')
def work_crawl():
    """
    文献工作流
    支持：化学应急源 + 不良反应 + 研究类型筛选
    """
    
    body = request.get_json(silent=True) or {}
    
    # 获取参数
    chemical = body.get('chemical', [])
    adverse = body.get('adverse', [])
    maxResults = int(body.get('maxResults') or 50)
    source = body.get('source', 'pubmed')
    study_type = body.get('studyType', '') or None

    
    # 验证必需参数
    if not chemical or not adverse:
        print('[Enhanced Literature Crawl] 缺少必需参数')
        return jsonify({'code': 'BadRequest', 'message': '化学应急源和不良反应为必填项'}), 400
    
    try:
        # 初始化百度翻译服务
        if not BaiduTranslationService:
            return jsonify({
                'success': False,
                'message': '百度翻译服务不可用'
            }), 500
        translator = BaiduTranslationService()
        
        # 翻译化学应急源和不良反应为英文（用于PubMed搜索）
        chemical_source_en = translator.translate_batch(chemical, 'auto', 'en')
        adverse_reaction_en = translator.translate_batch(adverse, 'auto', 'en')
        
        # 调用PubMed API爬虫（使用英文关键词）
        results = pubmed_api_crawler(
            chemical_source=chemical_source_en,
            adverse_reaction=adverse_reaction_en,
            study_type=study_type,
            translator=translator,
            max_results=maxResults,  # 最多获取100条
            start_year=2000,  # 从2000年开始
            end_year=datetime.now().year
        )
        
        print(f'爬取完成，共获取 {len(results)} 条文献')

        # 保存到 literature_filter 表
        saved_count = 0
        for item in results:
            try:
                # 构建搜索关键词
                search_keyword = f"{chemical_source}-{adverse_reaction}"
                
                # 解析日期
                _dt = _parse_datetime(item.get('date'))
                
                # 创建 LiteratureFilter 记录
                lf = LiteratureFilter(
                    source='pubmed',
                    title=item.get('title_zh') or item.get('title') or '',
                    pmid=item.get('pmid') or '',
                    authors=_to_authors_json(item.get('author')),
                    publish_date=_dt.date() if isinstance(_dt, datetime) else None,
                    literature_type=item.get('literature_type') or 'other',
                    search_keyword=search_keyword,
                    abstract=item.get('abstract_zh') or item.get('abstract'),
                    keywords=item.get('keywords'),
                    link=item.get('link'),
                )
                db.session.add(lf)
                db.session.flush()
                saved_count += 1
                
            except Exception as e:
                print(f'[Enhanced Literature Crawl] 保存文献失败: {e}')
                continue
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'crawled': len(results),
            'results': results
        })
        
    except Exception as e:
        db.session.rollback()
        print(f'[Enhanced Literature Crawl] 爬取失败: {e}')
        return jsonify({'code': 'InternalError', 'message': str(e)}), 500

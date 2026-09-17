from flask import Blueprint, request, jsonify
from .. import db
from ..models import Toxicity, ToxicityHealthHazard
import json

bp = Blueprint('toxicity', __name__)


def _normalize_keyword(keyword: str) -> str | None:
    """标准化关键词"""
    if not keyword:
        return None
    return str(keyword).strip().lower()


def _clean_keyword_for_translation(keyword: str) -> str:
    """
    清洗关键词用于翻译
    - 删除括号及其内容：避蚊胺(deet) -> 避蚊胺
    - 删除特殊符号和标点
    - 保留中英文字母和数字
    """
    if not keyword:
        return keyword
    
    import re
    
    # 删除各种括号及其内容
    cleaned = re.sub(r'[（(][^）)]*[）)]', '', keyword)
    cleaned = re.sub(r'[【\[][^\】\]]*[】\]]', '', cleaned)
    cleaned = re.sub(r'[「『][^」』]*[」』]', '', cleaned)
    
    # 删除常见的特殊符号和标点，但保留中英文、数字、连字符
    cleaned = re.sub(r'[^\u4e00-\u9fff\u3400-\u4dbfa-zA-Z0-9\-\s]', '', cleaned)
    
    # 清理多余空格
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    
    return cleaned


@bp.get('/')
def list_toxicity():
    """获取毒性数据列表"""
    page = int(request.args.get('page', 1) or 1)
    page_size = int(request.args.get('pageSize', 20) or 20)
    page_size = max(1, min(100, page_size))

    q = Toxicity.query.order_by(Toxicity.id.desc())
    
    total = q.count()
    items = q.offset((page - 1) * page_size).limit(page_size).all()

    def to_dict(t: Toxicity):
        return {
            'id': str(t.id),
            'name': t.name,
            'rtecs_number': t.rtecs_number,
            'cas_number': t.cas_number,
            'chemical_name': t.chemical_name,
            'molecular_formula': t.molecular_formula,
            'molecular_weight': t.molecular_weight,
            'compound_descriptor': t.compound_descriptor,
            'synonyms': t.synonyms,
            'health_hazards_count': len(t.health_hazards),
            'created_at': t.created_at.isoformat() if t.created_at else None,
        }

    return jsonify({
        'items': [to_dict(t) for t in items],
        'page': page,
        'pageSize': page_size,
        'total': total
    })


@bp.get('/search')
def search_toxicity():
    """搜索毒性数据"""
    search_keyword = request.args.get('searchKeyword')
    page = int(request.args.get('page', 1) or 1)
    page_size = int(request.args.get('pageSize', 20) or 20)
    page_size = max(1, min(100, page_size))

    if not search_keyword or not search_keyword.strip():
        # 返回空集合
        return jsonify({'items': [], 'page': page, 'pageSize': page_size, 'total': 0})

    # 直接通过 search_keyword 字段查询
    q = Toxicity.query.filter(Toxicity.search_keyword == search_keyword.strip()).order_by(Toxicity.id.desc())
    
    total = q.count()
    items = q.offset((page - 1) * page_size).limit(page_size).all()

    def to_dict(t: Toxicity):
        # 翻译化合物描述符和健康危害数据
        try:
            from ..services.chemical_translator import translate_english_term_to_chinese
            
            # 翻译化合物描述符
            compound_descriptor_zh = translate_english_term_to_chinese(t.compound_descriptor) if t.compound_descriptor else None
            
            # 翻译健康危害数据
            translated_hazards = []
            for hh in t.health_hazards:
                translated_hazards.append({
                    'experiment_type': hh.experiment_type,
                    'experiment_type_zh': translate_english_term_to_chinese(hh.experiment_type) if hh.experiment_type else None,
                    'exposure_route': hh.exposure_route,
                    'exposure_route_zh': translate_english_term_to_chinese(hh.exposure_route) if hh.exposure_route else None,
                    'test_species': hh.test_species,
                    'test_species_zh': translate_english_term_to_chinese(hh.test_species) if hh.test_species else None,
                    'duration': hh.duration,
                    'toxic_effects': hh.toxic_effects,
                    'toxic_effects_zh': translate_english_term_to_chinese(hh.toxic_effects) if hh.toxic_effects else None,
                })
        except Exception as e:
            print(f"翻译健康危害数据失败: {e}")
            compound_descriptor_zh = t.compound_descriptor
            translated_hazards = [
                {
                    'experiment_type': hh.experiment_type,
                    'experiment_type_zh': hh.experiment_type,
                    'exposure_route': hh.exposure_route,
                    'exposure_route_zh': hh.exposure_route,
                    'test_species': hh.test_species,
                    'test_species_zh': hh.test_species,
                    'duration': hh.duration,
                    'toxic_effects': hh.toxic_effects,
                    'toxic_effects_zh': hh.toxic_effects,
                } for hh in t.health_hazards
            ]
        
        return {
            'id': str(t.id),
            'name': t.name,
            'search_keyword': t.search_keyword,
            'rtecs_number': t.rtecs_number,
            'chemical_name': t.chemical_name,
            'molecular_formula': t.molecular_formula,
            'molecular_weight': t.molecular_weight,
            'compound_descriptor': t.compound_descriptor,
            'compound_descriptor_zh': compound_descriptor_zh,
            'synonyms': t.synonyms,
            'health_hazards': translated_hazards,
            'created_at': t.created_at.isoformat() if t.created_at else None,
        }

    return jsonify({
        'items': [to_dict(t) for t in items],
        'page': page,
        'pageSize': page_size,
        'total': total
    })


@bp.post('/crawl')
def crawl_and_ingest():
    """爬取毒性数据并入库"""
    body = request.get_json(silent=True) or {}
    keywords_override = body.get('keywordsOverride')

    # 获取关键词
    if keywords_override and isinstance(keywords_override, list):
        raw_k = [str(x) for x in keywords_override]
    else:
        return jsonify({'code': 'BadRequest', 'message': 'keywordsOverride is required'}), 400

    K = [k.strip() for k in raw_k if k and k.strip()]
    
    if not K:
        return jsonify({'code': 'BadRequest', 'message': 'No keywords available for crawling'}), 400

    # 清洗关键词用于翻译（删除括号、特殊符号等）
    cleaned_keywords = [_clean_keyword_for_translation(k) for k in K]
    print(f"Original keywords: {K}")
    print(f"Cleaned keywords: {cleaned_keywords}")
    
    # 使用专业化学物质翻译（毒性数据库需要准确的英文化学名称）
    try:
        from ..services.chemical_translator import translate_chemical_names
        translated_keywords = translate_chemical_names(cleaned_keywords)
        print(f"Chemical translation results: {translated_keywords}")
    except Exception as e:
        print(f"Chemical translation failed, using cleaned keywords: {e}")
        translated_keywords = cleaned_keywords

    # 调用爬虫（改为后台线程，立即返回，避免请求阻塞/超时）
    try:
        import threading
        from flask import current_app
        from ..services.crawler.Toxicity_Database import search_chemical

        app = current_app._get_current_object()

        def _job(K_local: list[str], cleaned_local: list[str], translated_local: list[str]) -> None:
            try:
                with app.app_context():
                    for i, kw in enumerate(K_local):
                        try:
                            english_kw = translated_local[i] if i < len(translated_local) else kw
                            data = []
                            try:
                                data = search_chemical(english_kw) or []
                            except Exception as e:
                                print(f"Crawler failed for '{english_kw}': {e}")
                                data = []
                            for item in data:
                                try:
                                    _upsert_toxicity(item, kw)
                                except Exception as e_item:
                                    print(f"Error upserting toxicity item for '{kw}': {e_item}")
                                    continue
                        except Exception as e_loop:
                            print(f"Error crawling toxicity data for keyword '{kw}': {e_loop}")
                            continue
            except Exception as e_outer:
                print(f"toxicity crawl background job error: {e_outer}")

        t = threading.Thread(target=_job, args=(K, cleaned_keywords, translated_keywords), daemon=True)
        t.start()

        return jsonify({'success': True, 'started': True})

    except ImportError:
        return jsonify({'code': 'ServiceUnavailable', 'message': 'Toxicity crawler not available'}), 503
    except Exception as e:
        return jsonify({'code': 'InternalServerError', 'message': str(e)}), 500


def _upsert_toxicity(item: dict, keyword: str):
    """插入或更新毒性数据"""
    try:
        # 提取基本信息
        name = item.get('名称', '')
        data = item.get('数据', {})
        external_id = item.get('id', '')
        
        if not name:
            return None, False

        # 查找是否已存在（同一来源+外部ID+关键词）
        existing = None
        if external_id and keyword:
            existing = Toxicity.query.filter_by(
                source='rtecs', 
                external_id=external_id,
                search_keyword=keyword.strip()
            ).first()
        
        if not existing and keyword:
            # 尝试按名称和关键词查找
            existing = Toxicity.query.filter_by(
                name=name,
                search_keyword=keyword.strip()
            ).first()

        # 准备数据
        toxicity_data = {
            'source': 'rtecs',
            'external_id': external_id or None,
            'name': name,
            'search_keyword': keyword.strip() if keyword else None,
            'rtecs_number': data.get('RTECS编号'),
            'chemical_name': data.get('化学名称'),
            'cas_number': data.get('CAS注册号'),
            'beilstein_ref': data.get('BEILSTEIN参考号'),
            'last_update': data.get('最后更新'),
            'reference_count': int(data.get('引用数据项', 0)) if data.get('引用数据项', '').isdigit() else None,
            'molecular_formula': data.get('分子式'),
            'molecular_weight': data.get('分子量'),
            'wiswesser_line': data.get('WISWESSER线路标记'),
            'compound_descriptor': data.get('化合物描述符'),
            'synonyms': data.get('同义词/商标名称'),
            'raw_payload': json.dumps(item, ensure_ascii=False)
        }

        is_created = False
        if existing:
            # 更新现有记录
            for key, value in toxicity_data.items():
                if key != 'source':  # 不更新source字段
                    setattr(existing, key, value)
            toxicity = existing
        else:
            # 创建新记录
            toxicity = Toxicity(**toxicity_data)
            db.session.add(toxicity)
            is_created = True

        db.session.flush()  # 获取ID

        # 处理健康危害数据
        if is_created:
            health_hazards = data.get('健康危害数据', [])
            for hh in health_hazards:
                hazard = ToxicityHealthHazard(
                    toxicity_id=toxicity.id,
                    experiment_type=hh.get('实验类型', ''),
                    exposure_route=hh.get('暴露途径'),
                    test_species=hh.get('观察物种'),
                    duration=hh.get('duration'),
                    toxic_effects=hh.get('毒性效应'),
                    reference=hh.get('参考文献')
                )
                db.session.add(hazard)

        db.session.commit()
        return toxicity, is_created

    except Exception as e:
        db.session.rollback()
        print(f"Error upserting toxicity data: {e}")
        return None, False


@bp.delete('/<int:toxicity_id>')
def delete_toxicity(toxicity_id: int):
    """删除毒性数据"""
    toxicity = Toxicity.query.get(toxicity_id)
    if not toxicity:
        return jsonify({'code': 'NotFound', 'message': 'toxicity data not found'}), 404

    db.session.delete(toxicity)
    db.session.commit()
    return jsonify({'success': True})


@bp.get('/<int:toxicity_id>')
def get_toxicity(toxicity_id: int):
    """获取单个毒性数据详情"""
    toxicity = Toxicity.query.get(toxicity_id)
    if not toxicity:
        return jsonify({'code': 'NotFound', 'message': 'toxicity data not found'}), 404

    return jsonify({
        'id': str(toxicity.id),
        'name': toxicity.name,
        'rtecs_number': toxicity.rtecs_number,
        'chemical_name': toxicity.chemical_name,
        'cas_number': toxicity.cas_number,
        'beilstein_ref': toxicity.beilstein_ref,
        'last_update': toxicity.last_update,
        'reference_count': toxicity.reference_count,
        'molecular_formula': toxicity.molecular_formula,
        'molecular_weight': toxicity.molecular_weight,
        'wiswesser_line': toxicity.wiswesser_line,
        'compound_descriptor': toxicity.compound_descriptor,
        'synonyms': toxicity.synonyms,
        'health_hazards': [
            {
                'id': hh.id,
                'experiment_type': hh.experiment_type,
                'exposure_route': hh.exposure_route,
                'test_species': hh.test_species,
                'duration': hh.duration,
                'toxic_effects': hh.toxic_effects,
                'reference': hh.reference
            } for hh in toxicity.health_hazards
        ],
        'raw_payload': toxicity.raw_payload,
        'created_at': toxicity.created_at.isoformat() if toxicity.created_at else None,
        'updated_at': toxicity.updated_at.isoformat() if toxicity.updated_at else None,
    })

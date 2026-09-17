from flask import Blueprint, request, jsonify
from datetime import datetime
from sqlalchemy.exc import IntegrityError
from sqlalchemy import case
import hashlib
from .. import db
from ..models import Recall, Recall_filter, Product


bp = Blueprint('recall', __name__)


def _parse_datetime(value):
    if not value:
        return None
    try:
        if isinstance(value, str):
            v = value.strip()
            for fmt in [
                '%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M', '%Y/%m/%d %H:%M:%S', '%Y/%m/%d %H:%M',
                '%Y-%m-%d', '%Y/%m/%d', '%Y.%m.%d', '%Y%m%d', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%dT%H:%M:%SZ'
            ]:
                try:
                    return datetime.strptime(v, fmt)
                except ValueError:
                    pass
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(int(value))
    except Exception:
        return None
    return None


def _clean_text(s: str | None) -> str | None:
    if s is None:
        return None
    try:
        import html, re
        t = html.unescape(s)
        t = re.sub(r"<[^>]+>", "", t)
        t = re.sub(r"[\u200B-\u200D\uFEFF]", "", t)
        t = re.sub(r"\s+", " ", t).strip()
        return t
    except Exception:
        return s


def _gen_external_id(source: str, item: dict) -> str:
    ext = item.get('id') or item.get('externalId')
    if ext:
        return str(ext)
    any_text = f"{item.get('生产厂家') or ''}|{item.get('产品名称') or ''}|{item.get('时间') or ''}"
    raw = f"{source}|{any_text}"
    return hashlib.sha1(raw.encode('utf-8')).hexdigest()


def _apply_time_order(query):
    nulls_last = case((Recall.time.is_(None), 1), else_=0)
    return query.order_by(nulls_last.asc(), Recall.time.desc(), Recall.id.desc())


def _insert_recall_to_filter(source: str, item: dict, search_keyword: str = None):
    """
    将爬虫数据插入到recall_filter初筛表
    返回：(对象, 是否新建, 错误信息)
    """
    title = _clean_text(item.get('产品名称') or '')
    if not title:
        return None, False, 'title required'
    
    ext_id = _gen_external_id(source, item)
    dt = _parse_datetime(item.get('时间'))

    # 检查是否已存在（避免重复）
    obj = Recall_filter.query.filter_by(source=source, external_id=ext_id).first()
    created = False
    
    if obj is None:
        obj = Recall_filter(
            source=source,
            external_id=ext_id,
            search_keyword=search_keyword,
            manufacturer=_clean_text(item.get('生产厂家')),
            product_name=title,
            description=_clean_text(item.get('产品描述')),
            defect=_clean_text(item.get('产品缺陷')),
            hazard=_clean_text(item.get('危害')),
            time=dt,
            link=item.get('link') or None,
        )
        db.session.add(obj)
        db.session.flush()
        created = True
    else:
        # 如果已存在，更新updated_at时间戳和搜索关键词
        if search_keyword:
            obj.search_keyword = search_keyword
        obj.updated_at = datetime.utcnow()
        db.session.flush()
    
    return obj, created, None


def _upsert_recall_and_bind(pid: int, source: str, item: dict):
    title = _clean_text(item.get('产品名称') or '')
    if not title:
        return None, 'title required'
    ext_id = _gen_external_id(source, item)
    dt = _parse_datetime(item.get('时间'))

    obj = Recall.query.filter_by(source=source, external_id=ext_id).first()
    created = False
    if obj is None:
        obj = Recall(
            source=source,
            external_id=ext_id,
            manufacturer=_clean_text(item.get('生产厂家')),
            product_name=title,
            description=_clean_text(item.get('产品描述')),
            defect=_clean_text(item.get('产品缺陷')),
            hazard=_clean_text(item.get('危害')),
            time=dt,
            link=item.get('link') or None,
        )
        db.session.add(obj)
        db.session.flush()
        created = True
    else:
        # 补全缺失字段
        obj.manufacturer = obj.manufacturer or _clean_text(item.get('生产厂家'))
        obj.product_name = obj.product_name or title
        obj.description = obj.description or _clean_text(item.get('产品描述'))
        obj.defect = obj.defect or _clean_text(item.get('产品缺陷'))
        obj.hazard = obj.hazard or _clean_text(item.get('危害'))
        obj.time = obj.time or dt
        obj.link = obj.link or item.get('link') or None
        db.session.flush()

    # 记录召回ID用于Neo4j同步
    recall_id = obj.id

    bound = 0
    # 暂时移除关键词绑定功能，因为 RecallKeyword 模型不存在
    # bind_with = item.get('bindWith') or []

    # 同步到Neo4j
    try:
        from ..services.neo4j_sync import sync_to_neo4j
        operation = 'create' if created else 'update'
        if created or bound > 0:
            sync_to_neo4j('recall', recall_id, operation)
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"Failed to sync recall {recall_id} to Neo4j: {e}")

    return obj, created, bound, None


@bp.get('/search')
def search_recall_local_first():
    product_id = request.args.get('productId')
    product_name = request.args.get('productName')
    # 可选关键词过滤
    keyword_filter = request.args.get('keyword')
    page = int(request.args.get('page', 1) or 1)
    page_size = int(request.args.get('pageSize', 20) or 20)
    page_size = max(1, min(100, page_size))

    pid = None
    if product_id:
        try:
            pid = int(product_id)
        except (TypeError, ValueError):
            pid = None
    if pid is None and product_name:
        p = Product.query.filter_by(name=str(product_name)).first()
        pid = p.id if p else None

    if pid is None:
        return jsonify({'items': [], 'page': page, 'pageSize': page_size, 'total': 0})

    # 暂时移除产品关键词功能，因为 ProductKeyword 模型不存在
    norm_k = []
    if keyword_filter:
        kf = str(keyword_filter).strip().lower()
        norm_k = [kf] if kf else []

    items = []
    total = 0
    # 暂时移除关键词绑定查询功能，因为 RecallKeyword 模型不存在
    # 直接返回空结果

    def to_dict(x: Recall):
        return {
            'id': str(x.id),
            'source': x.source,
            'manufacturer': x.manufacturer,
            'productName': x.product_name,
            'description': x.description,
            'defect': x.defect,
            'hazard': x.hazard,
            'time': x.time.isoformat(sep=' ') if x.time else None,
            'link': x.link,
        }

    return jsonify({'items': [to_dict(x) for x in items], 'page': page, 'pageSize': page_size, 'total': total})


@bp.post('/crawl')
def crawl_and_ingest():
    body = request.get_json(silent=True) or {}
    product_id = body.get('productId')
    product_name = body.get('productName')
    keywords_override = body.get('keywordsOverride')

    pid = None
    if product_id is not None:
        try:
            pid = int(product_id)
        except (TypeError, ValueError):
            pid = None
    if pid is None and product_name:
        p = Product.query.filter_by(name=str(product_name)).first()
        pid = p.id if p else None
    if pid is None:
        return jsonify({'code': 'BadRequest', 'message': 'product not found or invalid'}), 400

    # 关键词集合 K：优先使用 keywordsOverride，否则从数据库获取
    if keywords_override and isinstance(keywords_override, list):
        raw_k = [str(x) for x in keywords_override]
    else:
        # 暂时移除产品关键词功能，因为 ProductKeyword 模型不存在
        raw_k = []
    K = sorted(set([str(k).strip().lower() for k in raw_k if str(k).strip()]))
    
    # 如果没有关键词，直接返回
    if not K:
        return jsonify({'code': 'BadRequest', 'message': 'No keywords available for crawling'}), 400

    # 导入用户将放置的爬虫函数
    from app.services.crawler.JiangsuRecall import JiangsuRecall
    from app.services.crawler.EUROPARecall import EUROPARecall
    from app.services.crawler.ASEANRecall import ASEANRecall
    from app.services.crawler.OECDRecall import OECDRecall
    from app.services.crawler.KoreanSearchRecall import KoreanSearchRecall
    from app.services.crawler.JapaneseConsumerRecall import JapaneseConsumerRecall
    from app.services.crawler.AustralianRecall import AustralianRecall

    site_map = [
        ('江苏省缺陷产品管理技术中心', JiangsuRecall),
        ('欧盟委员会非食品类快速预警系统', EUROPARecall),
        ('东盟召回产品信息', ASEANRecall),
        ('经合组织', OECDRecall),
        ('韩国检索召回信息网', KoreanSearchRecall),
        ('日本消费者厅召回信息网站', JapaneseConsumerRecall),
        ('澳大利亚召回', AustralianRecall),
    ]

    summary = {s: {"requested": 0, "crawled": 0, "created": 0, "updated": 0, "bindings": 0} for s, _ in site_map}
    by_kw = []

    try:
        # 若覆盖传入则全量执行；否则按补齐策略执行
        targets = K
        for kw in targets:
            kw_created = 0
            kw_updated = 0
            kw_bound = 0
            for site, fn in site_map:
                summary[site]["requested"] += 1
                try:
                    # 若为韩国站点，搜索关键词需翻译为韩文
                    if site == '韩国检索召回信息网':
                        from app.services.translator import translate_to_ko
                        ko_kw = translate_to_ko([kw])[0] or kw
                        data = fn(ko_kw) or []
                    else:
                        data = fn(kw) or []
                except Exception:
                    data = []
                summary[site]["crawled"] += len(data)
                for item in data:
                    # 韩国站点：入库保留原始韩文，仅拼接链接
                    if site == '韩国检索召回信息网':
                        uid = item.get('UID') or item.get('id')
                        link = f"https://www.safetykorea.kr/recall/ajax/fRecallBoard?recallUid={uid}" if uid else item.get('link')
                        mapped = {
                            'id': str(uid) if uid else None,
                            '生产厂家': item.get('COMPANYNAME'),
                            '产品名称': item.get('PRODUCTNAME'),
                            '产品描述': item.get('MODEL'),
                            '产品缺陷': None,
                            '危害': None,
                            '时间': item.get('PUBLISHDATE'),
                            'link': link,
                            'bindWith': [kw],
                        }
                    elif site == '日本消费者厅召回信息网站':
                        # 结构示例：
                        # {'category': '...', 'image': '...', 'title': '...', 'link': '...rcl=00000033094...', 'publish_date': '2024/11/11', 'action_date': '2024/11/07'}
                        lk = item.get('link')
                        rid = None
                        try:
                            if lk and 'rcl=' in lk:
                                import urllib.parse as up
                                qs = up.urlparse(lk).query
                                rid = dict(up.parse_qsl(qs)).get('rcl')
                        except Exception:
                            rid = None
                        mapped = {
                            'id': str(rid) if rid else None,
                            '生产厂家': None,
                            '产品名称': item.get('title'),
                            '产品描述': item.get('category'),
                            '产品缺陷': None,
                            '危害': None,
                            '时间': item.get('publish_date') or item.get('action_date'),
                            'link': lk,
                            'bindWith': [kw],
                        }
                    else:
                        mapped = {
                            'id': item.get('id'),
                            '生产厂家': item.get('生产厂家'),
                            '产品名称': item.get('产品名称'),
                            '产品描述': item.get('产品描述'),
                            '产品缺陷': item.get('产品缺陷'),
                            '危害': item.get('危害'),
                            '时间': item.get('时间'),
                            'link': item.get('link'),
                            'bindWith': [kw],
                        }
                    obj, is_created, bound_cnt, err = _upsert_recall_and_bind(pid, site, mapped)
                    if obj is None and err:
                        continue
                    kw_created += 1 if is_created else 0
                    kw_updated += 0 if is_created else 1
                    kw_bound += bound_cnt
                    summary[site]['created'] += 1 if is_created else 0
                    summary[site]['updated'] += 0 if is_created else 1
                    summary[site]['bindings'] += bound_cnt
            by_kw.append({"keyword": kw, "created": kw_created, "updated": kw_updated, "bound": kw_bound})

        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({'code': 'Conflict', 'message': 'unique constraint violated'}), 409

    return jsonify({'summary': summary, 'byKeyword': by_kw})


@bp.delete('/<int:recall_id>')
def delete_recall(recall_id: int):
    x = Recall.query.get(recall_id)
    if not x:
        return jsonify({'code': 'NotFound', 'message': 'recall not found'}), 404
    
    # 同步删除到Neo4j
    try:
        from ..services.neo4j_sync import sync_to_neo4j
        sync_to_neo4j('recall', recall_id, 'delete')
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"Failed to delete recall {recall_id} from Neo4j: {e}")
    
    db.session.delete(x)
    db.session.commit()
    return jsonify({'success': True})


@bp.get('/filter')
def get_recall_filter():
    """
    获取召回初筛表数据
    支持按搜索关键词筛选（精确匹配 search_keyword 字段）
    """
    search_keyword = request.args.get('searchKeyword')
    page = int(request.args.get('page', 1) or 1)
    page_size = int(request.args.get('pageSize', 20) or 20)
    page_size = max(1, min(100, page_size))
    
    query = Recall_filter.query
    
    # 如果有搜索关键词，精确匹配 search_keyword 字段
    if search_keyword:
        query = query.filter(Recall_filter.search_keyword == search_keyword)
    
    # 按更新时间倒序排列
    query = query.order_by(Recall_filter.updated_at.desc())
    
    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    
    def to_dict(x: Recall_filter):
        return {
            'id': str(x.id),
            'source': x.source,
            'searchKeyword': x.search_keyword,
            'manufacturer': x.manufacturer,
            'productName': x.product_name,
            'description': x.description,
            'defect': x.defect,
            'hazard': x.hazard,
            'time': x.time.isoformat(sep=' ') if x.time else None,
            'link': x.link,
            'createdAt': x.created_at.isoformat(sep=' ') if x.created_at else None,
            'updatedAt': x.updated_at.isoformat(sep=' ') if x.updated_at else None,
        }
    
    return jsonify({
        'items': [to_dict(x) for x in items],
        'page': page,
        'pageSize': page_size,
        'total': total
    })


@bp.post('/filter/promote/<int:filter_id>')
def promote_recall_from_filter(filter_id: int):
    """
    将初筛表的召回数据移入正式表
    """
    filter_item = Recall_filter.query.get(filter_id)
    if not filter_item:
        return jsonify({'code': 'NotFound', 'message': 'Filter item not found'}), 404
    
    try:
        # 检查是否已存在
        existing = Recall.query.filter_by(
            source=filter_item.source,
            external_id=filter_item.external_id
        ).first()
        
        if existing:
            # 如果已存在，只删除初筛数据
            db.session.delete(filter_item)
            db.session.commit()
            return jsonify({'success': True, 'message': 'Already exists in recall table'})
        
        # 创建正式表记录
        recall_item = Recall(
            source=filter_item.source,
            external_id=filter_item.external_id,
            manufacturer=filter_item.manufacturer,
            product_name=filter_item.product_name,
            description=filter_item.description,
            defect=filter_item.defect,
            hazard=filter_item.hazard,
            time=filter_item.time,
            link=filter_item.link,
        )
        db.session.add(recall_item)
        db.session.flush()
        
        # 同步到Neo4j
        try:
            from ..services.neo4j_sync import sync_to_neo4j
            sync_to_neo4j('recall', recall_item.id, 'create')
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Failed to sync recall {recall_item.id} to Neo4j: {e}")
        
        # 删除初筛数据
        db.session.delete(filter_item)
        db.session.commit()
        
        return jsonify({'success': True, 'recallId': recall_item.id})
        
    except Exception as e:
        db.session.rollback()
        import logging
        logging.getLogger(__name__).error(f"Error promoting recall filter: {e}")
        return jsonify({'code': 'Error', 'message': str(e)}), 500


@bp.delete('/filter/<int:filter_id>')
def delete_recall_filter(filter_id: int):
    """
    删除初筛表的召回数据
    """
    filter_item = Recall_filter.query.get(filter_id)
    if not filter_item:
        return jsonify({'code': 'NotFound', 'message': 'Filter item not found'}), 404
    
    db.session.delete(filter_item)
    db.session.commit()
    return jsonify({'success': True})


@bp.post('/crawl-to-filter')
def crawl_to_filter():
    """
    爬取召回数据并存入初筛表（recall_filter）
    
    请求体示例：
    {
        "keywords": ["玩具", "儿童用品"],  // 搜索关键词列表
        "sources": ["中国SAMR"],          // 可选：指定数据源，不传则爬取所有源
        "max_pages": 1                    // 可选：每个关键词爬取的最大页数
    }
    """
    body = request.get_json(silent=True) or {}
    keywords = body.get('keywords', [])
    sources_filter = body.get('sources', [])  # 可选：筛选特定数据源
    max_pages = body.get('max_pages', 1)
    
    if not keywords or not isinstance(keywords, list):
        return jsonify({'code': 'BadRequest', 'message': 'keywords required'}), 400
    
    # 导入爬虫函数
    from app.services.crawler.ChinaSAMRRecall import ChinaSAMRRecall
    from app.services.crawler.JiangsuRecall import JiangsuRecall
    from app.services.crawler.EUROPARecall import EUROPARecall
    from app.services.crawler.ASEANRecall import ASEANRecall
    from app.services.crawler.OECDRecall import OECDRecall
    from app.services.crawler.KoreanSearchRecall import KoreanSearchRecall
    from app.services.crawler.JapaneseConsumerRecall import JapaneseConsumerRecall
    from app.services.crawler.AustralianRecall import AustralianRecall
    
    # 爬虫配置：(数据源名称, 爬虫函数)
    site_map = [
        ('中国SAMR', ChinaSAMRRecall),
        ('江苏省缺陷产品管理技术中心', JiangsuRecall),
        ('欧盟委员会非食品类快速预警系统', EUROPARecall),
        ('东盟召回产品信息', ASEANRecall),
        ('经合组织', OECDRecall),
        ('韩国检索召回信息网', KoreanSearchRecall),
        ('日本消费者厅召回信息网站', JapaneseConsumerRecall),
        ('澳大利亚召回', AustralianRecall),
    ]
    
    # 如果指定了sources，则只爬取指定的源
    if sources_filter:
        site_map = [(name, fn) for name, fn in site_map if name in sources_filter]
    
    summary = {s: {"crawled": 0, "created": 0, "updated": 0} for s, _ in site_map}
    by_keyword = []
    
    try:
        for kw in keywords:
            kw = str(kw).strip()
            if not kw:
                continue
                
            kw_created = 0
            kw_updated = 0
            
            for site_name, crawler_fn in site_map:
                try:
                    # 特殊处理：韩国站点需要翻译关键词
                    if site_name == '韩国检索召回信息网':
                        try:
                            from app.services.translator import translate_to_ko
                            ko_kw = translate_to_ko([kw])[0] or kw
                            data = crawler_fn(ko_kw) or []
                        except Exception:
                            data = []
                    # 中国SAMR支持max_pages参数
                    elif site_name == '中国SAMR':
                        data = crawler_fn(kw, max_pages=max_pages) or []
                    else:
                        data = crawler_fn(kw) or []
                        
                except Exception as e:
                    import logging
                    logging.getLogger(__name__).warning(f"Crawler {site_name} failed for keyword '{kw}': {e}")
                    data = []
                
                summary[site_name]["crawled"] += len(data)
                
                # 将爬取的数据存入初筛表
                for item in data:
                    # 韩国站点特殊处理
                    if site_name == '韩国检索召回信息网':
                        uid = item.get('UID') or item.get('id')
                        link = f"https://www.safetykorea.kr/recall/ajax/fRecallBoard?recallUid={uid}" if uid else item.get('link')
                        mapped = {
                            'id': str(uid) if uid else None,
                            '生产厂家': item.get('COMPANYNAME'),
                            '产品名称': item.get('PRODUCTNAME'),
                            '产品描述': item.get('MODEL'),
                            '产品缺陷': None,
                            '危害': None,
                            '时间': item.get('PUBLISHDATE'),
                            'link': link,
                        }
                    # 日本站点特殊处理
                    elif site_name == '日本消费者厅召回信息网站':
                        lk = item.get('link')
                        rid = None
                        try:
                            if lk and 'rcl=' in lk:
                                import urllib.parse as up
                                qs = up.urlparse(lk).query
                                rid = dict(up.parse_qsl(qs)).get('rcl')
                        except Exception:
                            rid = None
                        mapped = {
                            'id': str(rid) if rid else None,
                            '生产厂家': None,
                            '产品名称': item.get('title'),
                            '产品描述': item.get('category'),
                            '产品缺陷': None,
                            '危害': None,
                            '时间': item.get('publish_date') or item.get('action_date'),
                            'link': lk,
                        }
                    else:
                        # 通用数据映射
                        mapped = {
                            'id': item.get('id'),
                            '生产厂家': item.get('生产厂家'),
                            '产品名称': item.get('产品名称'),
                            '产品描述': item.get('产品描述'),
                            '产品缺陷': item.get('产品缺陷'),
                            '危害': item.get('危害'),
                            '时间': item.get('时间'),
                            'link': item.get('link'),
                        }
                    
                    # 插入到初筛表，传入搜索关键词
                    obj, is_created, err = _insert_recall_to_filter(site_name, mapped, search_keyword=kw)
                    if obj is None and err:
                        continue
                    
                    if is_created:
                        kw_created += 1
                        summary[site_name]['created'] += 1
                    else:
                        kw_updated += 1
                        summary[site_name]['updated'] += 1
            
            by_keyword.append({
                "keyword": kw,
                "created": kw_created,
                "updated": kw_updated
            })
        
        db.session.commit()
        
    except IntegrityError as e:
        db.session.rollback()
        import logging
        logging.getLogger(__name__).error(f"Database integrity error: {e}")
        return jsonify({'code': 'Conflict', 'message': 'Database constraint violated'}), 409
    except Exception as e:
        db.session.rollback()
        import logging
        logging.getLogger(__name__).error(f"Unexpected error in crawl_to_filter: {e}")
        return jsonify({'code': 'Error', 'message': str(e)}), 500
    
    return jsonify({
        'success': True,
        'summary': summary,
        'byKeyword': by_keyword
    })



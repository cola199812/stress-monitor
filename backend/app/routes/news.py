from flask import Blueprint, request, jsonify
from datetime import datetime
from sqlalchemy.exc import IntegrityError
from sqlalchemy import case
from .. import db
from ..models import News, News_filter, ProductSymptom, ProductSymptomNews, Product, Symptom3, Symptom2
from app.utils.common import clean_text, parse_datetime
from ..services.neo4j_sync import Neo4jSyncService
from ..services.crawler.news import BaiduNewsCrawler, ChinaNewsCrawler, SohuNewsCrawler


bp = Blueprint('news', __name__)


@bp.get('/')
def list_news():
    """获取新闻列表，支持前端数据管理功能"""

    nulls_last = case((News.publish_time.is_(None), 1), else_=0)
    q = News.query.order_by(nulls_last.asc(), News.publish_time.desc(), News.id.desc())
    items = q.all()
    
    def to_dict(x: News):
        # 查询新闻的所有实体关系
        news_entity_relations = []
        try:
            # 查询该新闻作为佐证数据的所有产品-症状关系
            relation_sources = db.session.query(ProductSymptomNews).join(
                ProductSymptom, ProductSymptomNews.product_symptom_id == ProductSymptom.id
            ).join(
                Product, ProductSymptom.product_id == Product.id
            ).join(
                Symptom2, ProductSymptom.symptom_id == Symptom2.id
            ).filter(ProductSymptomNews.news_id == x.id).all()
            
            for relation_source in relation_sources:
                product_name = relation_source.product_symptom.product.name
                symptom_name = relation_source.product_symptom.symptom.symptom_name
                news_entity_relations.append({
                    'relation': f"{product_name} - {symptom_name}",
                    'type': 'product-symptom',
                    'product_id': relation_source.product_symptom.product_id,
                    'symptom_id': relation_source.product_symptom.symptom_id
                })
        except Exception as e:
            print(f"查询新闻 {x.id} 的实体关系失败: {e}")
        
        return {
            'id': str(x.id),
            'source': x.source,
            'source_wz': getattr(x, 'source_wz', None),
            'title': x.title,
            'publishTime': x.publish_time.isoformat() if x.publish_time else None,
            'publishDate': x.publish_time.isoformat()[:10] if x.publish_time else None,
            'abstract': x.abstract,
            'link': x.link,
            'state': bool(getattr(x, 'state', 0)),  # 转换为布尔值以匹配前端
            'authors': None,  # 新闻模型中没有authors字段，保持兼容性
            'entityRelations': news_entity_relations  # 返回所有实体关系的数组
        }
    
    return jsonify([to_dict(x) for x in items])


def _clean_text_local(s: str | None) -> str | None:
    return clean_text(s)


def _apply_publish_time_order(query):
    nulls_last = case((News.publish_time.is_(None), 1), else_=0)
    return query.order_by(nulls_last.asc(), News.publish_time.desc(), News.id.desc())


def _save_to_news_filter(item: dict, source: str, search_keyword: str):
    """保存新闻到 News_filter 表"""
    title = _clean_text_local(item.get('NewsTitle') or '').strip()
    if not title:
        return None, False, 'title is required'
    
    link = item.get('NewsUrl')
    dt = parse_datetime(item.get('PublishTime'))

    # 去重策略：按 source + title + search_keyword 去重
    # 简化去重逻辑，移除对external_id和link_normalized的依赖
    obj = News_filter.query.filter_by(
        source=source, 
        title=title, 
        search_keyword=search_keyword
    ).first()

    created = False
    if obj is None:
        obj = News_filter(
            source=source,
            title=title,
            publish_time=dt,
            abstract=_clean_text_local(item.get('Abstract')),
            source_wz=item.get('SourceWz', ''),  # 保存新闻原始来源
            link=link,
            search_keyword=search_keyword,
        )
        db.session.add(obj)
        db.session.flush()
        created = True
    else:
        # 轻量更新：仅补全空字段
        obj.publish_time = obj.publish_time or dt
        obj.abstract = obj.abstract or _clean_text_local(item.get('Abstract'))
        obj.source_wz = obj.source_wz or item.get('SourceWz', '')  # 更新新闻原始来源
        obj.link = obj.link or link
        db.session.flush()

    return obj, created, None


@bp.get('/filter')
def list_news_filter():
    """列出暂存在 news_filter 的采集结果。"""
    
    search_keyword = request.args.get('searchKeyword')

    q = News_filter.query
    
    # 如果提供了搜索关键词，按关键词筛选（支持模糊匹配）
    if search_keyword:
        q = q.filter(News_filter.search_keyword.like(f'%{search_keyword}%'))
    
    q = q.order_by(News_filter.id.desc())
    
    items = q.all()  # 返回所有数据，不分页
    
    def to_dict(x: News_filter):
        return {
            'id': str(x.id),
            'source': x.source,
            'source_wz': getattr(x, 'source_wz', None),
            'title': x.title,
            'publishTime': x.publish_time.isoformat() if x.publish_time else None,
            'searchKeyword': x.search_keyword,
            'abstract': x.abstract,
            'link': x.link,
            'ai_relevance': x.ai_relevance,
            'ai_reason': x.ai_reason,
            'product': x.product,
            'symptom': x.symptom
        }
    
    return jsonify([to_dict(x) for x in items])


@bp.get('/search')
def search_news_local_first():
    """简化版：返回所有新闻，按发布时间倒序排列"""
    import logging
    logger = logging.getLogger(__name__)
    
    page = int(request.args.get('page', 1) or 1)
    page_size = int(request.args.get('pageSize', 20) or 20)
    page_size = max(1, min(100, page_size))

    logger.info(f'[News Search] 查询参数 - page: {page}, pageSize: {page_size}')

    # 查询所有新闻，按发布时间倒序
    q = _apply_publish_time_order(News.query)
    total = q.count()
    items = q.offset((page - 1) * page_size).limit(page_size).all()
    
    logger.info(f'[News Search] 查询结果总数: {total}, 返回 {len(items)} 条记录')

    def to_dict(x: News):
        return {
            'id': str(x.id),
            'source': x.source,
            'source_wz': getattr(x, 'source_wz', None),
            'title': clean_text(x.title),
            'publishTime': x.publish_time.isoformat(sep=' ') if x.publish_time else None,
            'publishDate': x.publish_time.isoformat()[:10] if x.publish_time else None,
            'abstract': clean_text(x.abstract),
            'url': x.link,
            'link': x.link,
            'state': getattr(x, 'state', None),
            'authors': None,
            'entityRelation': None
        }

    return jsonify({'items': [to_dict(x) for x in items], 'page': page, 'pageSize': page_size, 'total': total})


##################前端入库功能##################
@bp.post('/filter/promote/<int:filter_id>')
def promote_filter_item(filter_id: int):
    """将 news_filter 中的单条记录转存到 news 表"""
    
    x = News_filter.query.get(filter_id)
    if not x:
        return jsonify({'code': 'NotFound', 'message': 'filter item not found'}), 404

    try:
        # 简单按标题去重：若已存在则跳过创建
        existed = News.query.filter_by(title=x.title, link=x.link).first()
        if existed is None:
            obj = News(
                source=x.source,
                source_wz=x.source_wz,
                title=x.title,
                publish_time=x.publish_time,
                abstract=x.abstract,
                link=x.link,
                state=0  # 默认为待处理状态
            )
            db.session.add(obj)
            db.session.flush()
        
        # 删除 filter 项
        db.session.delete(x)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        print(f'[News Filter] 入库失败: {e}', exc_info=True)
        return jsonify({'code': 'InternalError', 'message': str(e)}), 500



@bp.post('/crawl')
def crawl_and_ingest():
    body = request.get_json(silent=True) or {}
    print(f'[News Crawl] 收到爬取请求: {body}')
    
    keywords_override = body.get('keywordsOverride')
    max_results = body.get('maxResults', 10)  # 每个关键词最大爬取数量，默认10条

    # 简化版：直接使用 keywordsOverride 作为关键词
    if keywords_override and isinstance(keywords_override, list):
        raw_k = [str(x) for x in keywords_override]
        print(f'[News Crawl] 使用覆盖关键词: {raw_k}')
    else:
        # 如果没有提供关键词，返回错误
        print('[News Crawl] 缺少必需参数: keywordsOverride')
        return jsonify({'code': 'BadRequest', 'message': 'keywordsOverride is required'}), 400
    
    K = sorted(set([str(k).strip() for k in raw_k if str(k).strip()]))
    
    # 如果没有关键词，直接返回
    if not K:
        print('[News Crawl] 没有有效关键词')
        return jsonify({'code': 'BadRequest', 'message': 'No keywords available for crawling'}), 400

    print(f'[News Crawl] 最终关键词列表: {K}')
    
    # 简化版：直接爬取所有关键词
    targets = K
    
    # 导入百度新闻爬虫
    from app.services.crawler.news.BaiduNews import BaiduNewsCrawler

    # 只使用百度新闻
    summary = {"baidu": {"requested": 0, "crawled": 0, "created": 0, "updated": 0, "bindings": 0}}
    by_kw = []

    try:
        # 创建百度新闻爬虫实例
        crawler = BaiduNewsCrawler()
        
        for kw in targets:
            kw_created = 0
            kw_updated = 0
            kw_bound = 0

            summary["baidu"]["requested"] += 1
            print(f'[News Crawl] 调用百度新闻爬虫，关键词: {kw}')
            
            # 调用百度新闻爬虫
            data = crawler.crawl(
                keyword=kw,
                max_results=max_results
            ) or []
            
            print(f'[News Crawl] 百度新闻爬虫返回 {len(data)} 条数据')
            summary["baidu"]["crawled"] += len(data)
            
            for item in data:
                # 映射数据格式到 news_filter 表结构
                mapped = {
                    'NewsTitle': item.get('title') or '',
                    'NewsUrl': item.get('url'),
                    'PublishTime': item.get('time'),
                    'Abstract': item.get('content', '')[:200] if item.get('content') else '',  # 摘要取前200字符
                    'SourceWz': item.get('source_wz', ''),  # 添加新闻原始来源字段
                }
                obj, is_created, err = _save_to_news_filter(mapped, 'baidu', kw)
                if obj is None and err:
                    print(f'[News Crawl] 保存失败: {err}')
                    continue
                kw_created += 1 if is_created else 0
                kw_updated += 0 if is_created else 1
                summary['baidu']['created'] += 1 if is_created else 0
                summary['baidu']['updated'] += 0 if is_created else 1
                
            by_kw.append({"keyword": kw, "created": kw_created, "updated": kw_updated, "bound": kw_bound})

        db.session.commit()
        print(f'[News Crawl] 爬取完成，统计: {summary}')
    except IntegrityError as e:
        db.session.rollback()
        print(f'[News Crawl] 数据库冲突: {e}')
        return jsonify({'code': 'Conflict', 'message': 'unique constraint violated'}), 409
    except Exception as e:
        db.session.rollback()
        print(f'[News Crawl] 未知错误: {e}')
        return jsonify({'code': 'InternalError', 'message': str(e)}), 500

    print(f'[News Crawl] 返回结果: summary={summary}, byKeyword={by_kw}')
    return jsonify({'summary': summary, 'byKeyword': by_kw})


##################自动爬取的api##################
#################################################
@bp.post('/crawl/test')
def crawl():
    body = request.get_json(silent=True) or {}
    
    keywords_override = body.get('keywordsOverride')
    max_results = body.get('maxResults', 10)
    source = body.get('source')

    # 校验关键词
    if keywords_override and isinstance(keywords_override, list):
        raw_k = [str(x) for x in keywords_override]
    else:
        return jsonify({'code': 'BadRequest', 'message': 'keywordsOverride is required'}), 400
    
    # 校验来源参数
    if not source:
        return jsonify({'code': 'BadRequest', 'message': 'source is required'}), 400
    
    # 处理source参数类型，支持多数据源
    sources = []
    if isinstance(source, list):
        if len(source) == 0:
            return jsonify({'code': 'BadRequest', 'message': 'source list cannot be empty'}), 400
        sources = [str(s).strip().lower() for s in source]
    elif isinstance(source, str):
        sources = [str(source).strip().lower()]
    else:
        return jsonify({'code': 'BadRequest', 'message': 'source must be a string or list'}), 400
    
    # 支持的爬虫来源映射
    crawler_mapping = {
        'baidu': BaiduNewsCrawler,
        'sohu': SohuNewsCrawler,
        'chinanews': ChinaNewsCrawler
    }
    
    # 验证所有数据源是否支持
    invalid_sources = [s for s in sources if s not in crawler_mapping]
    if invalid_sources:
        return jsonify({'code': 'BadRequest', 'message': f'Unsupported sources: {invalid_sources}. Available sources: {list(crawler_mapping.keys())}'}), 400
    
    K = sorted(set([str(k).strip() for k in raw_k if str(k).strip()]))

    if not K:
        return jsonify({'code': 'BadRequest', 'message': 'No keywords available'}), 400

    # 为每个数据源创建summary结构
    summary = {}
    for src in sources:
        summary[src] = {
            "requested": 0,
            "crawled": 0
        }

    by_kw = []
    all_items = []

    try:
        # 遍历每个数据源进行采集
        for source_name in sources:
            # 根据source参数选择对应的爬虫类
            CrawlerClass = crawler_mapping[source_name]
            crawler = CrawlerClass()

            # 为当前数据源收集关键词统计
            source_by_kw = []
            
            for kw in K:
                summary[source_name]["requested"] += 1

                try:
                    data = crawler.crawl(
                        keyword=kw,
                        max_results=max_results
                    ) or []

                    summary[source_name]["crawled"] += len(data)

                    # 👉 核心：处理每个关键词的数据
                    for item in data:
                        all_items.append({
                            "keyword": kw,
                            "title": item.get("title", ""),
                            "url": item.get("url", ""),
                            "publish_time": item.get("time", ""),
                            "content": item.get("content", ""),
                            "source": item.get("source", ""),  # 爬虫来源名称
                            "source_wz": item.get("source_wz", "")  # 原始发布来源
                        })

                    # 添加关键词统计
                    source_by_kw.append({
                        "keyword": kw,
                        "count": len(data),
                        "source": source_name
                    })

                except Exception as kw_error:
                    # 添加失败的关键词统计
                    source_by_kw.append({
                        "keyword": kw,
                        "count": 0,
                        "source": source_name,
                        "error": str(kw_error)
                    })
            
            # 将当前数据源的关键词统计添加到总体统计中
            by_kw.extend(source_by_kw)

    except Exception as e:
        return jsonify({'code': 'InternalError', 'message': str(e)}), 500

    # 打印每个来源的采集数量
    print(f'[News Crawl] 采集统计:')
    for source_name, stats in summary.items():
        print(f'  {source_name}: 请求 {stats["requested"]} 个关键词，采集到 {stats["crawled"]} 条数据')
    
    return jsonify({
        "summary": summary,
        "byKeyword": by_kw,
        "items": all_items
    })


##################自动爬取后入库##################
@bp.post('/storage')
def news_storage():
    """新闻存储 - 批量入库新闻数据"""
    try:
        body = request.get_json(silent=True) or {}
        data = body.get('data')
        
        if not data or not isinstance(data, list):
            return jsonify({'code': 'BadRequest', 'message': 'data field is required and must be a list'}), 400

        if len(data) == 0:
            return jsonify({'code': 'BadRequest', 'message': 'data list cannot be empty'}), 400

        created_count = 0
        
        for item in data:
            try:
                # 数据验证
                if not isinstance(item, dict):
                    continue

                # 获取必要字段
                url = item.get('url')
                if not url:
                    continue

                # 检查是否已经存在（按URL去重）
                existing = News_filter.query.filter_by(link=url).first()
                if existing:
                    continue

                # 处理发布时间
                publish_time = None
                if item.get('publish_time'):
                    try:
                        if isinstance(item['publish_time'], str):
                            from datetime import datetime
                            # 简单的时间解析
                            if len(item['publish_time']) == 10:  # YYYY-MM-DD格式
                                publish_time = datetime.strptime(item['publish_time'], '%Y-%m-%d')
                        elif isinstance(item['publish_time'], datetime):
                            publish_time = item['publish_time']
                    except Exception:
                        pass

                # 处理产品和症状信息
                product = ''
                symptom = ''
                p_s_data = item.get('p_s', {})
                if isinstance(p_s_data, dict):
                    product = p_s_data.get('product', '')
                    symptom = p_s_data.get('symptom', '')
                elif isinstance(p_s_data, list) and len(p_s_data) > 0:
                    first_ps = p_s_data[0] if isinstance(p_s_data[0], dict) else {}
                    product = first_ps.get('product', '')
                    symptom = first_ps.get('symptom', '')

                print(item.get('title'))

                # 创建新记录
                news_filter = News_filter(
                    source=item.get('source', ''),
                    source_wz=item.get('source_wz', ''),
                    title=item.get('title', ''),
                    search_keyword=item.get('keyword', ''),
                    publish_time=publish_time,
                    abstract=item.get('abstract'),
                    link=url,
                    ai_relevance=item.get('relevance', ''),
                    ai_reason=item.get('ai_reason', ''),
                    product=product,
                    symptom=symptom
                )
                
                db.session.add(news_filter)
                created_count += 1

            except Exception:
                continue

        # 提交事务
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Successfully stored {created_count} news items'
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({
            'code': 'InternalError', 
            'message': f'Failed to store news data: {str(e)}'
        }), 500


@bp.delete('/filter/<int:filter_id>')
def delete_news_filter(filter_id: int):
    """删除 news_filter 中的记录"""
    x = News_filter.query.get(filter_id)
    if not x:
        return jsonify({'code': 'NotFound', 'message': 'news filter item not found'}), 404
    
    db.session.delete(x)
    db.session.commit()
    return jsonify({'success': True})


@bp.post('/create')
def create_news():
    """创建新闻"""
    import logging
    logger = logging.getLogger(__name__)
    
    data = request.get_json()
    if not data:
        return jsonify({'code': 'BadRequest', 'message': 'No data provided'}), 400
    
    basic_info = data.get('basicInfo', {})
    entity_relations = data.get('entityRelations', [])
    
    # 验证必需字段
    if not basic_info.get('title') or not basic_info.get('source'):
        return jsonify({'code': 'BadRequest', 'message': 'Title and source are required'}), 400
    
    try:      
        # 根据是否有实体关系设置state
        has_entity_relations = len(entity_relations) > 0
        news_state = 1 if has_entity_relations else 0
        
        # 创建新闻记录
        news = News(
            source=basic_info['source'],
            source_wz=basic_info.get('source_wz'),
            title=basic_info['title'],
            publish_time=basic_info['publishTime'],
            abstract=basic_info.get('abstract'),
            link=basic_info.get('link'),
            state=news_state  # 根据实体关系设置状态
        )
        
        db.session.add(news)
        db.session.flush()
        
        # 处理实体关系
        created_relations = []
        for relation in entity_relations:
            product_id = relation.get('productId')
            symptom_id = relation.get('symptomId')
            
            if product_id and symptom_id:
                # 查找或创建产品-症状关系
                product_symptom = ProductSymptom.query.filter_by(
                    product_id=product_id,
                    symptom_id=symptom_id
                ).first()
                
                if not product_symptom:
                    # 创建新的产品-症状关系
                    product_symptom = ProductSymptom(
                        product_id=product_id,
                        symptom_id=symptom_id,
                    )
                    db.session.add(product_symptom)
                    db.session.flush()

                    # 同步新增的产品-症状关系到 Neo4j
                    try:
                        Neo4jSyncService.sync_product_symptom_relation(
                            product_id=product_id,
                            symptom_id=symptom_id,
                            relation_id=product_symptom.id,
                            operation='create'
                        )
                    except Exception as e:
                        logger.warning(f"[News] Neo4j 同步产品-症状关系失败(create): {e}")
                
                # 直接创建新的新闻-产品症状关联记录
                news_source = ProductSymptomNews(
                    product_symptom_id=product_symptom.id,
                    news_id=news.id,
                    evidence_strength=1.0
                )
                db.session.add(news_source)
                
                created_relations.append({
                    'product_id': product_id,
                    'symptom_id': symptom_id,
                    'relation_id': product_symptom.id
                })
        
        # # 同步到Neo4j
        # try:
        #     from ..services.neo4j_sync import sync_to_neo4j
        #     sync_to_neo4j('news', news.id, 'create')
        # except Exception as e:
        #     logger.warning(f"Failed to sync news {news.id} to Neo4j: {e}")
        
        db.session.commit()
        print(f'[News] 创建成功: {news.title}')
        
        return jsonify({
            'success': True,
            'id': str(news.id),
            'message': '新闻创建成功',
            'entityRelations': created_relations
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f'[News] 创建失败: {e}', exc_info=True)
        return jsonify({'code': 'InternalError', 'message': str(e)}), 500


@bp.put('/<int:news_id>')
def update_news(news_id: int):
    """更新新闻"""
    import logging
    logger = logging.getLogger(__name__)
    
    news = News.query.get(news_id)
    if not news:
        return jsonify({'code': 'NotFound', 'message': 'News not found'}), 404
    
    data = request.get_json()
    if not data:
        return jsonify({'code': 'BadRequest', 'message': 'No data provided'}), 400
    
    basic_info = data.get('basicInfo', {})
    entity_relations = data.get('entityRelations', [])

    try:
        # 1. 更新基本信息
        news.title = basic_info['title']
        news.publish_time = datetime.fromisoformat(basic_info['publishTime'])
        news.source = basic_info['source']
        news.source_wz = basic_info.get('source_wz')
        news.abstract = basic_info.get('abstract')
        news.link = basic_info['link']
        
        # 根据是否有实体关系设置状态
        has_entity_relations = len(entity_relations) > 0
        news.state = 1 if has_entity_relations else 0

        # 2. 删除该新闻的所有现有关系
        existing_sources = ProductSymptomNews.query.filter_by(
            news_id=news_id
        ).all()
        for source in existing_sources:
            db.session.delete(source)

        # 3. 添加新的关系
        updated_relations = []
        for relation in entity_relations:
            product_id = relation.get('productId')
            symptom_id = relation.get('symptomId')
            
            if product_id and symptom_id:
                # 查找或创建ProductSymptom
                product_symptom = ProductSymptom.query.filter_by(
                    product_id=product_id,
                    symptom_id=symptom_id
                ).first()
                
                if not product_symptom:
                    # 创建新的产品-症状关系
                    product_symptom = ProductSymptom(
                        product_id=product_id,
                        symptom_id=symptom_id,
                    )
                    db.session.add(product_symptom)
                    db.session.flush()

                    # 同步到Neo4j
                    try:
                        Neo4jSyncService.sync_product_symptom_relation(
                            product_id=product_id,
                            symptom_id=symptom_id,
                            relation_id=product_symptom.id,
                            operation='create'
                        )
                    except Exception as e:
                        logger.warning(f"[News] Neo4j 同步产品-症状关系失败(create): {e}")

                # 创建新的新闻-产品症状关联记录
                news_source = ProductSymptomNews(
                    product_symptom_id=product_symptom.id,
                    news_id=news_id,
                    evidence_strength=1.0
                )
                db.session.add(news_source)
                
                updated_relations.append({
                    'product_id': product_id,
                    'symptom_id': symptom_id,
                    'relation_id': product_symptom.id
                })

        db.session.commit()
        logger.info(f'[News] 更新成功: {news.title}')
        
        return jsonify({
            'success': True,
            'message': '新闻更新成功',
            'entityRelations': updated_relations
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f'[News] 更新失败: {e}', exc_info=True)
        return jsonify({'code': 'InternalError', 'message': str(e)}), 500


@bp.delete('/<int:news_id>')
def delete_news(news_id: int):
    """删除新闻"""
    import logging
    logger = logging.getLogger(__name__)
    
    news = News.query.get(news_id)
    if not news:
        return jsonify({'code': 'NotFound', 'message': 'News not found'}), 404
    
    try:
        # 删除相关的新闻-产品症状关联记录
        existing_sources = ProductSymptomNews.query.filter_by(news_id=news_id).all()
        
        for source in existing_sources:
            db.session.delete(source)
        
        logger.info(f'[News] 删除新闻 {news_id} 相关的 {len(existing_sources)} 条关联记录')
        
        # 同步删除到Neo4j（在MySQL删除之前）
        # try:
        #     from ..services.neo4j_sync import sync_to_neo4j
        #     sync_to_neo4j('news', news_id, 'delete')
        # except Exception as e:
        #     logger.warning(f"Failed to delete news {news_id} from Neo4j: {e}")
        
        # 删除新闻记录
        db.session.delete(news)
        db.session.commit()
        
        logger.info(f'[News] 删除成功: {news.title}')
        return jsonify({
            'success': True,
            'message': '新闻删除成功'
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f'[News] 删除失败: {e}', exc_info=True)
        return jsonify({'code': 'InternalError', 'message': str(e)}), 500


@bp.get('/relations')
def get_product_symptom_relations():
    """获取所有已有的产品-症状关系，用于实体关系选择"""
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        # 查询所有已有的产品-症状关系
        relations = db.session.query(ProductSymptom).join(
            Product, ProductSymptom.product_id == Product.id
        ).join(
            Symptom2, ProductSymptom.symptom_id == Symptom2.id
        ).all()
        
        logger.info(f'[News] 查询到 {len(relations)} 个产品-症状关系')
        
        # 返回关系列表，包含产品和症状信息
        relation_list = []
        product_dict = {}
        symptom_dict = {}
        
        for relation in relations:
            relation_data = {
                'id': str(relation.id),
                'productId': str(relation.product_id),
                'symptomId': str(relation.symptom_id),
                'productName': relation.product.name,
                'symptomName': relation.symptom.symptom_name,
                'confidence': relation.confidence
            }
            relation_list.append(relation_data)
            
            # 收集产品和症状信息
            product_dict[str(relation.product_id)] = {
                'id': str(relation.product_id),
                'name': relation.product.name
            }
            symptom_dict[str(relation.symptom_id)] = {
                'id': str(relation.symptom_id),
                'name': relation.symptom.symptom_name
            }
        
        logger.info(f'[News] 返回 {len(relation_list)} 个产品-症状关系')
        
        return jsonify({
            'relations': relation_list,
            'products': list(product_dict.values()),
            'symptoms': list(symptom_dict.values())
        })
        
    except Exception as e:
        print(e)
        return jsonify({'code': 'InternalError', 'message': str(e)}), 500


@bp.get('/<int:news_id>')
def get_news_detail(news_id: int):
    """获取单个新闻详情，包含实体关系"""
    import logging
    logger = logging.getLogger(__name__)
    
    news = News.query.get(news_id)
    if not news:
        return jsonify({'code': 'NotFound', 'message': 'News not found'}), 404
    
    try:
        # 查询新闻的所有实体关系
        news_entity_relations = []
        relation_sources = db.session.query(ProductSymptomNews).join(
            ProductSymptom, ProductSymptomNews.product_symptom_id == ProductSymptom.id
        ).join(
            Product, ProductSymptom.product_id == Product.id
        ).join(
            Symptom2, ProductSymptom.symptom_id == Symptom2.id
        ).filter(ProductSymptomNews.news_id == news_id).all()
        
        for relation_source in relation_sources:
            news_entity_relations.append({
                'id': str(relation_source.id),
                'productId': str(relation_source.product_symptom.product_id),
                'symptomId': str(relation_source.product_symptom.symptom_id),
                'productName': relation_source.product_symptom.product.name,
                'symptomName': relation_source.product_symptom.symptom.symptom_name
            })
        
        return jsonify({
            'id': str(news.id),
            'source': news.source,
            'source_wz': getattr(news, 'source_wz', None),
            'title': news.title,
            'publishTime': news.publish_time.isoformat() if news.publish_time else None,
            'publishDate': news.publish_time.isoformat()[:10] if news.publish_time else None,
            'abstract': news.abstract,
            'link': news.link,
            'state': bool(getattr(news, 'state', 0)),
            'authors': None,
            'entityRelations': news_entity_relations
        })
        
    except Exception as e:
        logger.error(f'[News] 获取新闻详情失败: {e}', exc_info=True)
        return jsonify({'code': 'InternalError', 'message': str(e)}), 500



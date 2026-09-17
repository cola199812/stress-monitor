from flask import Flask
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
import os

# 加载环境变量
load_dotenv()

db = SQLAlchemy()


def create_app() -> Flask:
    app = Flask(__name__)

    # 允许 /path 与 /path/ 均可访问，避免 308 重定向
    app.url_map.strict_slashes = False

    # 基础配置：优先使用环境变量（PostgreSQL）
    app.config['POSTGRES_HOST'] = os.getenv('POSTGRES_HOST', '127.0.0.1')
    app.config['POSTGRES_PORT'] = int(os.getenv('POSTGRES_PORT', '5432'))
    app.config['POSTGRES_USER'] = os.getenv('POSTGRES_USER', 'postgres')
    app.config['POSTGRES_PASSWORD'] = os.getenv('POSTGRES_PASSWORD', '123456')
    app.config['POSTGRES_DB'] = os.getenv('POSTGRES_DB', 'medical_system')
    app.config['SQLALCHEMY_DATABASE_URI'] = f"postgresql+psycopg://{app.config['POSTGRES_USER']}:{app.config['POSTGRES_PASSWORD']}@{app.config['POSTGRES_HOST']}:{app.config['POSTGRES_PORT']}/{app.config['POSTGRES_DB']}"
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # 配置CORS，支持生产环境域名
    allowed_origins = [
        'http://localhost:3000', 
        'http://127.0.0.1:3000',
        'http://localhost:5050',  # 后端端口（用于代理Origin）
        'http://127.0.0.1:5050',  # 后端端口（用于代理Origin）
        'https://127.0.0.1:5050', # 后端端口HTTPS
        'http://localhost:3001', 
        'http://127.0.0.1:3001',
        'https://stressor.iepose.cn',  # 生产环境前端域名
        'http://stressor.iepose.cn',   # 生产环境前端域名（HTTP版本）
        'https://yingjiyuan.iepose.cn',  # 新的生产环境前端域名
        'http://yingjiyuan.iepose.cn',
        'http://zzzzz.iepose.cn',  # 新的生产环境前端域名
        'https://zzzzz.iepose.cn',   # 新的生产环境前端域名（HTTPS版本）
        'https://woyouyiji.iepose.cn', # 生产环境后端域名
        'http://woyouyiji.iepose.cn',  # 生产环境后端域名（HTTP版本）
        'https://192.168.1.71:50500',  # 内网HTTPS地址
        'http://192.168.1.71:50500',   # 内网HTTP地址
        'http://172.23.0.2:52301',     # 反向代理后端地址
    ]
    
    # 从环境变量获取额外的允许源
    env_origins = os.getenv('CORS_ORIGINS', '').split(',')
    if env_origins and env_origins[0]:
        allowed_origins.extend([origin.strip() for origin in env_origins if origin.strip()])
    
    CORS(app, 
         resources={
             r"/*": {
                 "origins": allowed_origins,
                 "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
                 "allow_headers": [
                     "Content-Type", 
                     "Authorization", 
                     "X-Requested-With", 
                     "Accept", 
                     "Origin",
                     "Access-Control-Request-Method",
                     "Access-Control-Request-Headers"
                 ],
                 "supports_credentials": True,
                 "max_age": 3600  # 预检请求缓存1小时
             }
         },
         supports_credentials=True
    )
    db.init_app(app)

    # 启动后台翻译线程（仅启动一次，线程为daemon，不阻塞退出）
    try:
        from .services.translator import start_background_translation
        start_background_translation(app)
    except Exception:
        pass

    # 注册蓝图
    from .routes.categories import bp as categories_bp
    from .routes.types import bp as types_bp
    from .routes.products import bp as products_bp
    from .routes.allergens import bp as allergens_bp
    from .routes.symptoms import bp as symptoms_bp
    from .routes.complaints import bp as complaints_bp
    from .routes.literature import bp as literature_bp
    from .routes.news import bp as news_bp
    from .routes.recall import bp as recall_bp
    from .routes.toxicity import bp as toxicity_bp
    from .routes.collection import bp as collection_bp
    from .routes.knowledge import bp as knowledge_bp
    from .routes.dashboard import bp as dashboard_bp
    from .routes.info_management import bp as info_management_bp
    from .routes.entity_management import bp as entity_bp
    from .routes.relationship_management import bp as relationship_bp
    from .routes.hazard_assessment import bp as hazard_assessment_bp
    app.register_blueprint(categories_bp, url_prefix='/categories')
    app.register_blueprint(types_bp, url_prefix='/types')
    app.register_blueprint(products_bp, url_prefix='/products')
    app.register_blueprint(allergens_bp, url_prefix='/allergens')
    app.register_blueprint(symptoms_bp, url_prefix='/symptoms')
    app.register_blueprint(complaints_bp, url_prefix='/complaints')
    app.register_blueprint(literature_bp, url_prefix='/literature')
    app.register_blueprint(news_bp, url_prefix='/news')
    app.register_blueprint(recall_bp, url_prefix='/recall')
    app.register_blueprint(toxicity_bp, url_prefix='/toxicity')
    app.register_blueprint(knowledge_bp, url_prefix='/knowledge')
    app.register_blueprint(collection_bp, url_prefix='/collection')
    app.register_blueprint(dashboard_bp, url_prefix='/dashboard')
    app.register_blueprint(info_management_bp, url_prefix='/info-management')
    app.register_blueprint(entity_bp, url_prefix='/entity')
    app.register_blueprint(relationship_bp, url_prefix='/relationship')
    app.register_blueprint(hazard_assessment_bp, url_prefix='/hazard-assessment')

    # 添加CORS预检请求处理
    @app.before_request
    def handle_preflight():
        from flask import request, jsonify
        if request.method == "OPTIONS":
            origin = request.headers.get('Origin')
            response = jsonify({'status': 'ok'})
            
            # 检查请求来源是否在允许列表中
            if origin and origin in allowed_origins:
                response.headers['Access-Control-Allow-Origin'] = origin
            elif origin and ('localhost' in origin or '127.0.0.1' in origin):
                # 对于本地开发，允许localhost
                response.headers['Access-Control-Allow-Origin'] = origin
            else:
                # 当来源不在允许列表中时，设置为默认允许的源之一
                # 这样可以避免当请求包含凭据时不能使用通配符'*'的错误
                response.headers['Access-Control-Allow-Origin'] = 'https://stressor.iepose.cn'
                
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization,X-Requested-With,Accept,Origin'
            response.headers['Access-Control-Allow-Methods'] = 'GET,PUT,POST,DELETE,OPTIONS,PATCH'
            response.headers['Access-Control-Allow-Credentials'] = 'true'
            response.headers['Access-Control-Max-Age'] = '3600'
            return response

    # 添加CORS响应头
    @app.after_request
    def after_request(response):
        from flask import request
        origin = request.headers.get('Origin')
        referer = request.headers.get('Referer')
        
        # 检查是否有转发头（代理场景）
        forwarded_host = request.headers.get('X-Forwarded-Host')
        forwarded_proto = request.headers.get('X-Forwarded-Proto', 'http')
        forwarded_for = request.headers.get('X-Forwarded-For')

        # 尝试从多个来源确定正确的Origin
        final_origin = None
        
        # 特殊处理：节点小宝代理场景
        # 当Origin是后端地址时，说明是通过代理访问，应该返回前端域名
        proxy_mapping = {
            'http://127.0.0.1:5050': 'http://yingjiyuan.iepose.cn',  # 本地后端 -> 前端代理域名
            'http://zzzzz.iepose.cn': 'http://yingjiyuan.iepose.cn', # 后端代理域名 -> 前端代理域名
        }
        
        if origin in proxy_mapping:
            final_origin = proxy_mapping[origin]
        
        # 1. 优先使用X-Forwarded-Host构造的origin
        if not final_origin and forwarded_host:
            forwarded_origin = f"{forwarded_proto}://{forwarded_host}"
            if forwarded_origin in allowed_origins:
                final_origin = forwarded_origin
        
        # 2. 检查Origin头
        if not final_origin and origin and origin in allowed_origins:
            final_origin = origin
        
        # 3. 尝试从Referer提取origin（代理可能不传Origin但传Referer）
        if not final_origin and referer:
            try:
                from urllib.parse import urlparse
                parsed = urlparse(referer)
                referer_origin = f"{parsed.scheme}://{parsed.netloc}"
                if referer_origin in allowed_origins:
                    final_origin = referer_origin
            except:
                pass
        
        # 4. 对于本地开发，允许localhost/127.0.0.1
        if not final_origin and origin and ('localhost' in origin or '127.0.0.1' in origin):
            final_origin = origin
        
        # 5. 最后的fallback
        if not final_origin:
            final_origin = 'http://yingjiyuan.iepose.cn'
        
        response.headers['Access-Control-Allow-Origin'] = final_origin
            
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization,X-Requested-With,Accept,Origin'
        response.headers['Access-Control-Allow-Methods'] = 'GET,PUT,POST,DELETE,OPTIONS,PATCH'
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        response.headers['Access-Control-Max-Age'] = '3600'
        
        return response

    # 健康检查
    @app.get('/health')
    def health():
        return {'status': 'ok'}
    
    
    # CORS测试端点
    @app.get('/cors-test')
    def cors_test():
        from flask import request
        return {
            'status': 'ok',
            'origin': request.headers.get('Origin'),
            'method': request.method,
            'allowed_origins': allowed_origins,
            'headers': dict(request.headers)
        }

    # 确保数据表存在（仅在未使用迁移工具时）
    with app.app_context():
        try:
            db.create_all(bind=None)
        except Exception:
            pass

    return app
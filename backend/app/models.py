from datetime import datetime
from . import db


# 医疗系统核心实体模型 - 基于实际数据库表结构

class Allergen(db.Model):
    """过敏原表"""
    __tablename__ = 'allergen'

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    name = db.Column(db.String(255), unique=True, nullable=False, comment='过敏原名称')
    cas_number = db.Column(db.String(64), nullable=True, comment='CAS号')
    description = db.Column(db.Text, nullable=True, comment='过敏原描述')
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    __table_args__ = (
        db.Index('idx_cas_number', 'cas_number'),
    )



class Literature(db.Model):
    """文献表"""
    __tablename__ = 'literature'

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    source = db.Column(db.String(32), nullable=False, comment='文献来源')
    title = db.Column(db.String(512), nullable=False, comment='文献标题')
    pmid = db.Column(db.String(64), nullable=True, comment='PubMed ID')
    authors = db.Column(db.Text, nullable=True, comment='作者')
    publish_date = db.Column(db.Date, nullable=True, comment='发布日期')
    literature_type = db.Column(db.String(128), nullable=True, comment='文献类型')
    abstract = db.Column(db.Text, nullable=True, comment='摘要')
    keywords = db.Column(db.Text, nullable=True, comment='关键词')
    state = db.Column(db.Integer, default=0, nullable=False, comment='状态')
    link = db.Column(db.String(1024), nullable=True, comment='链接')
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        db.UniqueConstraint('pmid', name='uk_literature_pmid'),
    )


class LiteratureFilter(db.Model):
    """文献临时筛选表（采集暂存）"""
    __tablename__ = 'literature_filter'

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    source = db.Column(db.String(32), nullable=False, comment='文献来源')
    title = db.Column(db.String(512), nullable=False, comment='文献标题')
    pmid = db.Column(db.String(64), nullable=True, comment='PubMed ID')
    authors = db.Column(db.Text, nullable=True, comment='作者(JSON或文本)')
    publish_date = db.Column(db.Date, nullable=True, comment='发布日期')
    literature_type = db.Column(db.String(128), nullable=True, comment='文献类型')
    search_keyword = db.Column(db.Text, nullable=False, comment='搜索关键词')
    abstract = db.Column(db.Text, nullable=True, comment='摘要')
    keywords = db.Column(db.Text, nullable=True, comment='关键词')
    link = db.Column(db.String(1024), nullable=True, comment='链接')
    # raw_payload = db.Column(db.Text, nullable=True, comment='原始抓取数据(JSON文本)')
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class Category(db.Model):
    """产品表1 - 基础产品表（顶级）"""
    __tablename__ = 'product_1'

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    name = db.Column(db.String(255), unique=True, nullable=False, comment='产品名称')
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # 关联关系：Product1 包含多个 Product2
    products2 = db.relationship('Type', backref='product1', cascade='all, delete-orphan')


class Type(db.Model):
    """产品表2 - 带分类的产品表（中级）"""
    __tablename__ = 'product_2'

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    category_id = db.Column(db.BigInteger, db.ForeignKey('product_1.id'), nullable=False, comment='分类ID')
    name = db.Column(db.String(255), unique=True, nullable=False, comment='产品名称')
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Product2 包含多个 Product3
    products3 = db.relationship('Product', backref='product2', cascade='all, delete-orphan')

    __table_args__ = (
        db.Index('idx_product2_parent', 'category_id'),
    )


class Product(db.Model):
    """产品表3 - 另一个带分类的产品表（下级）"""
    __tablename__ = 'product_3'

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    category_id = db.Column(db.BigInteger, db.ForeignKey('product_2.id'), nullable=False, comment='分类ID')
    name = db.Column(db.String(255), unique=True, nullable=False, comment='产品名称')
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


    __table_args__ = (
        db.Index('idx_product3_parent', 'category_id'),
    )

# 新闻实体与绑定
class News(db.Model):
    __tablename__ = 'news'

    id = db.Column(db.BigInteger, primary_key=True)
    source = db.Column(db.String(32), nullable=False, comment='来源网站')
    source_wz = db.Column(db.String(32), nullable=True, comment='具体来源')
    title = db.Column(db.String(512), nullable=False)
    publish_time = db.Column(db.DateTime, nullable=True)
    abstract = db.Column(db.Text, nullable=True, comment='关键信息')
    link = db.Column(db.String(255), nullable=True)
    state = db.Column(db.Integer, nullable=True, comment='状态')
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        db.Index('idx_news_publish_time', 'publish_time'),
        db.Index('idx_news_source', 'source'),
        db.UniqueConstraint('link', name='news_pk')
    )

class News_filter(db.Model):
    __tablename__ = 'news_filter'

    id = db.Column(db.BigInteger, primary_key=True)
    source = db.Column(db.String(32), nullable=False)
    source_wz = db.Column(db.String(32), nullable=True, comment='来源日报')
    search_keyword = db.Column(db.Text, nullable=False, comment='搜索关键词')
    title = db.Column(db.String(64), nullable=False)
    publish_time = db.Column(db.DateTime, nullable=True)
    abstract = db.Column(db.Text, nullable=True)
    link = db.Column(db.String(255), nullable=True)
    ai_relevance = db.Column(db.String(32), nullable=True, comment='ai分类')
    ai_reason = db.Column(db.Text, nullable=True, comment='ai分类原因')
    product = db.Column(db.String(16), nullable=True, comment='产品')
    symptom = db.Column(db.String(128), nullable=True, comment='不良反应')

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        db.Index('idx_news_publish_time', 'publish_time'),
        db.Index('idx_news_link_normalized', 'link'),
        db.UniqueConstraint('link', name='news_filter_pk_2')
    )


class Complaints(db.Model):
    __tablename__ = 'complaints'

    id = db.Column(db.BigInteger, primary_key=True)
    source = db.Column(db.String(32), nullable=False, comment='来源网站')
    title = db.Column(db.String(512), nullable=False)
    publish_time = db.Column(db.DateTime, nullable=True)
    abstract = db.Column(db.Text, nullable=True, comment='关键信息')
    link = db.Column(db.String(255), nullable=True)
    state = db.Column(db.Integer, nullable=True, comment='状态')
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        db.Index('complaints_publish_time', 'publish_time'),
        db.UniqueConstraint('link', name='complaints_pk')
    )


# 召回实体与绑定
class Recall(db.Model):
    __tablename__ = 'recall'

    id = db.Column(db.BigInteger, primary_key=True)
    # 来源：中文人类可读来源名
    source = db.Column(db.String(128), nullable=False)
    # 外部来源的主键/编号
    external_id = db.Column(db.String(128), nullable=True)

    manufacturer = db.Column(db.String(512), nullable=True)  # 生产厂家
    product_name = db.Column(db.String(1024), nullable=True)  # 产品名称
    description = db.Column(db.Text, nullable=True)  # 产品描述
    defect = db.Column(db.Text, nullable=True)  # 产品缺陷
    hazard = db.Column(db.Text, nullable=True)  # 危害
    time = db.Column(db.DateTime, nullable=True)  # 时间
    link = db.Column(db.String(1024), nullable=True)  # 可选链接

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        db.UniqueConstraint('source', 'external_id', name='uq_recall_source_extid'),
    )

# 召回实体与绑定
class Recall_filter(db.Model):
    __tablename__ = 'recall_filter'

    id = db.Column(db.BigInteger, primary_key=True)
    # 来源：中文人类可读来源名
    source = db.Column(db.String(128), nullable=False)
    # 外部来源的主键/编号
    external_id = db.Column(db.String(128), nullable=True)
    search_keyword = db.Column(db.Text, nullable=True, comment='搜索关键词')
    manufacturer = db.Column(db.String(512), nullable=True)  # 生产厂家
    product_name = db.Column(db.String(1024), nullable=True)  # 产品名称
    description = db.Column(db.Text, nullable=True)  # 产品描述
    defect = db.Column(db.Text, nullable=True)  # 产品缺陷
    hazard = db.Column(db.Text, nullable=True)  # 危害
    time = db.Column(db.DateTime, nullable=True)  # 时间
    link = db.Column(db.String(1024), nullable=True)  # 可选链接

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        db.UniqueConstraint('source', 'external_id', name='uq_recall_source_extid'),
    )


# 毒性数据模型
class Toxicity(db.Model):
    __tablename__ = 'toxicity'

    id = db.Column(db.BigInteger, primary_key=True)
    source = db.Column(db.String(32), nullable=False, default='rtecs')
    search_keyword = db.Column(db.Text, nullable=False, comment='搜索关键词')
    external_id = db.Column(db.String(128), nullable=True)
    name = db.Column(db.String(256), nullable=False)
    rtecs_number = db.Column(db.String(64), nullable=True)
    chemical_name = db.Column(db.Text, nullable=True)
    cas_number = db.Column(db.String(64), nullable=True)
    beilstein_ref = db.Column(db.String(128), nullable=True)
    last_update = db.Column(db.String(32), nullable=True)
    reference_count = db.Column(db.Integer, nullable=True)
    molecular_formula = db.Column(db.String(128), nullable=True)
    molecular_weight = db.Column(db.String(32), nullable=True)
    wiswesser_line = db.Column(db.Text, nullable=True)
    compound_descriptor = db.Column(db.String(128), nullable=True)
    synonyms = db.Column(db.JSON, nullable=True)
    raw_payload = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        db.UniqueConstraint('source', 'external_id', name='uk_source_external_id'),
        db.Index('idx_name', 'name'),
        db.Index('idx_cas_number', 'cas_number'),
        db.Index('idx_rtecs_number', 'rtecs_number'),
        db.Index('idx_search_keyword', 'search_keyword'),
    )

    # 关系
    health_hazards = db.relationship('ToxicityHealthHazard', backref='toxicity', cascade='all, delete-orphan')


# 毒性健康危害数据模型
class ToxicityHealthHazard(db.Model):
    __tablename__ = 'toxicity_health_hazard'

    id = db.Column(db.BigInteger, primary_key=True)
    toxicity_id = db.Column(db.BigInteger, db.ForeignKey('toxicity.id', ondelete='CASCADE'), nullable=False)
    experiment_type = db.Column(db.String(128), nullable=False)
    exposure_route = db.Column(db.String(64), nullable=True)
    test_species = db.Column(db.String(128), nullable=True)
    duration = db.Column(db.String(64), nullable=True)
    toxic_effects = db.Column(db.Text, nullable=True)
    reference = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class Symptom1(db.Model):
    """症状表1 - 基础症状表"""
    __tablename__ = 'symptom_1'

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    symptom_name = db.Column(db.String(256), unique=True, nullable=False, comment='症状名称')
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=True)

    # 关联关系
    symptoms2 = db.relationship('Symptom2', backref='symptom_1', cascade='all, delete-orphan')



class Symptom2(db.Model):
    """症状表2 - 带主要症状分类的症状表"""
    __tablename__ = 'symptom_2'

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    major_id = db.Column(db.BigInteger, db.ForeignKey('symptom_1.id'), nullable=False, comment='主要症状ID')
    symptom_name = db.Column(db.String(256), unique=True, nullable=False, comment='症状名称')
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # 关联关系
    symptom_3 = db.relationship('Symptom3', backref='symptom_2', cascade='all, delete-orphan')

    __table_args__ = (
        db.Index('idx_symptom2_parent', 'major_id'),
    )



class Symptom3(db.Model):
    """症状表3 - 带子症状分类的症状表"""
    __tablename__ = 'symptom_3'

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    sub_id = db.Column(db.BigInteger, db.ForeignKey('symptom_2.id'), nullable=False, comment='子症状ID')
    name = db.Column(db.String(256), unique=True, nullable=False, comment='症状名称')
    description = db.Column(db.JSON, nullable=True, comment='症状描述')
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=True)


    __table_args__ = (
        db.Index('idx_symptom3_parent', 'sub_id'),
    )


# 关联表模型

class AllergenProduct(db.Model):
    """过敏原-产品关联表"""
    __tablename__ = 'allergen_product'

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    product_id = db.Column(db.BigInteger, db.ForeignKey('product_3.id', ondelete='CASCADE'), nullable=False, comment='产品ID')
    allergen_id = db.Column(db.BigInteger, db.ForeignKey('allergen.id', ondelete='CASCADE'), nullable=False, comment='过敏原ID')
    exposure_score = db.Column(db.Float, nullable=True, comment='暴露潜力分数')
    exposure_details = db.Column(db.Text, nullable=True, comment='暴露潜力评分详情(JSON格式)')
    note = db.Column(db.Text, nullable=True, comment='备注')
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # 关联关系
    product = db.relationship('Product', backref='product_allergen')
    allergen = db.relationship('Allergen', backref='product_allergen')

    __table_args__ = (
        db.Index('idx_allergen_product', 'allergen_id', 'product_id'),
        db.Index('idx_product_allergen', 'product_id', 'allergen_id'),
    )


class ExposureScoringDetail(db.Model):
    """暴露潜力评分细节表"""
    __tablename__ = 'exposure_scoring_detail'

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    allergen_product_id = db.Column(db.BigInteger, db.ForeignKey('allergen_product.id', ondelete='CASCADE'), nullable=False, comment='过敏原-产品关联ID')
    age_score = db.Column(db.Integer, nullable=True, comment='年龄维度评分(1-4分)')
    product_form_score = db.Column(db.Integer, nullable=True, comment='产品形态维度评分(1-4分)')
    content_score = db.Column(db.Integer, nullable=True, comment='含量维度评分(1-4分)')
    frequency_score = db.Column(db.Integer, nullable=True, comment='使用频率维度评分(1-4分)')
    duration_score = db.Column(db.Integer, nullable=True, comment='使用时间维度评分(1-4分)')
    total_score = db.Column(db.Integer, nullable=True, comment='总分(5-20分)')
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # 关联关系
    allergen_product = db.relationship('AllergenProduct', backref='exposure_scoring_details')

    __table_args__ = (
        db.Index('idx_allergen_product_scoring', 'allergen_product_id'),
    )


class AllergenSymptom(db.Model):
    """过敏原-症状关联表"""
    __tablename__ = 'allergen_symptom'

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    allergen_id = db.Column(db.BigInteger, db.ForeignKey('allergen.id', ondelete='CASCADE'), nullable=False, comment='过敏原ID')
    symptom_id = db.Column(db.BigInteger, db.ForeignKey('symptom_2.id', ondelete='CASCADE'), nullable=False, comment='症状ID')
    traec_score = db.Column(db.Float, nullable=True, comment='TAREC评分')
    create_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    update_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # 关联关系
    symptom = db.relationship('Symptom2', backref='allergen_symptom')

    __table_args__ = (

        db.Index('idx_allergen_symptom', 'allergen_id', 'symptom_id'),
        db.Index('idx_symptom_allergen', 'symptom_id', 'allergen_id'),
    )


class AllergenProductSource(db.Model):
    """过敏原-产品来源表"""
    __tablename__ = 'allergen_product_source'
    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    allergen_product_id = db.Column(db.BigInteger, db.ForeignKey('allergen_product.id', ondelete='CASCADE'), nullable=False, comment='关联主表id')
    source_index_id = db.Column(db.BigInteger, db.ForeignKey('source_index.id', ondelete='CASCADE'), nullable=False, comment='统一来源表id')
    evidence_strength = db.Column(db.Float, nullable=False, comment='置信度')
    note = db.Column(db.String(256), nullable=True)

    # 关联关系
    allergen_product = db.relationship('AllergenProduct', backref='sources')
    source_index = db.relationship('SourceIndex', backref='allergen_product_sources')

    __table_args__ = (
        db.Index('allergen_product_id', 'allergen_product_id'),
        db.Index('source_index_id', 'source_index_id'),
    )

class ProductSymptom(db.Model):
    """产品与症状关系表"""
    __tablename__ = 'product_symptom'
    
    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True, comment='唯一id')
    product_id = db.Column(db.BigInteger, db.ForeignKey('product_3.id'), nullable=False, comment='过敏原id')
    symptom_id = db.Column(db.BigInteger, db.ForeignKey('symptom_2.id'), nullable=False, comment='分类症状id')
    PRR = db.Column(db.Float, nullable=True, comment='比例报告比')
    X_2 = db.Column(db.Float, nullable=True, comment='卡方值')
    create_at = db.Column(db.DateTime, nullable=False, server_default=db.text('CURRENT_TIMESTAMP'), comment='创建时间')
    update_at = db.Column(db.DateTime, nullable=False, server_default=db.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'), comment='更新时间')
    
    # 定义外键关系
    product = db.relationship('Product', backref=db.backref('symptoms', lazy='dynamic'))
    symptom = db.relationship('Symptom2', backref=db.backref('products', lazy='dynamic'))
    
    __table_args__ = (
        db.UniqueConstraint('product_id', 'symptom_id', name='uq_allergen_symptom'),
        db.Index('idx_symptom_product', 'symptom_id', 'product_id'),
    )


class AllergenSymptomSource(db.Model):
    """过敏原-症状来源表"""
    __tablename__ = 'allergen_symptom_source'
    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    allergen_symptom_id = db.Column(db.BigInteger, db.ForeignKey('allergen_symptom.id', ondelete='CASCADE'), nullable=False, comment='关联主表id')
    literature_id = db.Column(db.BigInteger, db.ForeignKey('literature.id', ondelete='CASCADE'), nullable=False, comment='文献来源_id')
    evidence_strength = db.Column(db.Float, nullable=False, comment='置信度')
    note = db.Column(db.String(256), nullable=True)

    # 关联关系
    allergen_symptom = db.relationship('AllergenSymptom', backref='sources')
    literature_index = db.relationship('Literature', backref='allergen_symptom_sources')

    __table_args__ = (
        db.Index('allergen_symptom_id', 'allergen_symptom_id'),
        db.Index('literature_id', 'literature_id'),
    )

class ProductSymptomNews(db.Model):
    """产品症状来源关联表"""
    __tablename__ = 'product_symptom_news'

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    product_symptom_id = db.Column(db.BigInteger, 
        db.ForeignKey('product_symptom.id', ondelete='CASCADE'), 
        nullable=False, 
        comment='产品-不良反应id'
    )
    news_id = db.Column(
        db.BigInteger, 
        db.ForeignKey('news.id'), 
        nullable=True, 
        comment='新闻_id'
    )
    evidence_strength = db.Column(
        db.Float, 
        nullable=True, 
        comment='置信度'
    )
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=True)

    # 定义关系
    product_symptom = db.relationship(
        'ProductSymptom', 
        backref=db.backref('sources', lazy='dynamic', cascade='all, delete-orphan')
    )
    news = db.relationship(
        'News', 
        backref=db.backref('product_symptom_sources', lazy='dynamic')
    )

    __table_args__ = (
        db.Index('product_symptom_id', 'product_symptom_id'),
        db.Index('news_id', 'news_id'),
    )


class ProductSymptomComp(db.Model):
    """产品症状来源关联表"""
    __tablename__ = 'product_symptom_complaints'

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    product_symptom_id = db.Column(
        db.BigInteger, 
        db.ForeignKey('product_symptom.id', ondelete='CASCADE'), 
        nullable=False, 
        comment='产品-不良反应id'
    )
    complaints_id = db.Column(
        db.BigInteger, 
        db.ForeignKey('complaints.id'), 
        nullable=False, 
        comment='投诉_id'
    )
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=True)

    # 定义关系
    product_symptom = db.relationship(
        'ProductSymptom', 
        backref=db.backref('complaint_sources', lazy='dynamic', cascade='all, delete-orphan')
    )
    complaint = db.relationship(
        'Complaints', 
        backref=db.backref('product_symptom_complaints', lazy='dynamic')
    )

    __table_args__ = (
        db.Index('product_symptom_id', 'product_symptom_id'),
        db.Index('complaints_id', 'complaints_id'),
    )


class SourceIndex(db.Model):
    """统一来源表"""
    __tablename__ = 'source_index'
    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True, comment='全局唯一来源ID')
    source_type = db.Column(db.Enum('literature', 'news', 'recall', name='source_type_enum'), nullable=False)
    source_ref_id = db.Column(db.BigInteger, nullable=False, comment='对应来源表的原始ID')
    title = db.Column(db.String(512), nullable=True)
    link = db.Column(db.String(1024), nullable=True)

    __table_args__ = (
        db.UniqueConstraint('source_type', 'source_ref_id', name='uq_source'),
    )


# 翻译缓存表（保持原有功能）
class TranslationCache(db.Model):
    """翻译缓存表"""
    __tablename__ = 'translation_cache'

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    src_text = db.Column(db.Text, nullable=False, comment='源文本')
    src_lang = db.Column(db.String(16), nullable=False, comment='源语言')
    tgt_lang = db.Column(db.String(16), nullable=False, comment='目标语言')
    result_text = db.Column(db.Text, nullable=False, comment='翻译结果')
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        db.Index('idx_translation_cache_key', 'src_lang', 'tgt_lang'),
    )


# 文献评分表模型

class LiteratureEpiScoring(db.Model):
    """流行病学研究评分表"""
    __tablename__ = 'literature_epi_scoring'

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True, comment='评分记录ID')
    literature_id = db.Column(db.BigInteger, db.ForeignKey('literature.id', ondelete='CASCADE'), nullable=False, comment='文献ID')
    relation_id = db.Column(db.BigInteger, db.ForeignKey('allergen_symptom.id', ondelete='SET NULL'), nullable=True, comment='关系ID')
    
    # 浓度权重 (Weight of Concentrations)
    mode_of_exposure = db.Column(db.Enum('inhalation', 'oral', 'dermal', name='exposure_mode_enum'), nullable=True, comment='暴露模式')
    type_of_biosample = db.Column(db.String(100), nullable=True, comment='生物样本类型')
    concentrations = db.Column(db.Numeric(15,6), nullable=True, comment='浓度')
    concentration_unit = db.Column(db.String(20), default='mg/L', comment='浓度单位')
    conversion_factor = db.Column(db.Numeric(10,4), nullable=True, comment='转换因子')
    concentration_weight = db.Column(db.Numeric(3,2), nullable=True, comment='浓度权重得分 (0-1分)')
    
    # 可靠性得分 (0-10分)
    reliability_q1_score = db.Column(db.Enum('0', '0.5', '1', name='reliability_score_enum'), default='1', nullable=True, comment='Q1得分')
    reliability_q1_comment = db.Column(db.Text, nullable=True, comment='Q1评论')
    reliability_q2_score = db.Column(db.Enum('0', '0.5', '1', name='reliability_score_enum'), default='1',  nullable=True, comment='Q2得分')
    reliability_q2_comment = db.Column(db.Text, nullable=True, comment='Q2评论')
    reliability_q3_score = db.Column(db.Enum('0', '0.5', '1', name='reliability_score_enum'), default='1', nullable=True, comment='Q3得分')
    reliability_q3_comment = db.Column(db.Text, nullable=True, comment='Q3评论')
    reliability_q4_score = db.Column(db.Enum('0', '0.5', '1', name='reliability_score_enum'), default='1', nullable=True, comment='Q4得分')
    reliability_q4_comment = db.Column(db.Text, nullable=True, comment='Q4评论')
    reliability_q5_score = db.Column(db.Enum('0', '0.5', '1', name='reliability_score_enum'), default='1', nullable=True, comment='Q5得分')
    reliability_q5_comment = db.Column(db.Text, nullable=True, comment='Q5评论')
    reliability_q6_score = db.Column(db.Enum('0', '0.5', '1', name='reliability_score_enum'), default='1', nullable=True, comment='Q6得分')
    reliability_q6_comment = db.Column(db.Text, nullable=True, comment='Q6评论')
    reliability_q7_score = db.Column(db.Enum('0', '0.5', '1', name='reliability_score_enum'), default='1', nullable=True, comment='Q7得分')
    reliability_q7_comment = db.Column(db.Text, nullable=True, comment='Q7评论')
    reliability_q8_score = db.Column(db.Enum('0', '0.5', '1', name='reliability_score_enum'), default='1', nullable=True, comment='Q8得分')
    reliability_q8_comment = db.Column(db.Text, nullable=True, comment='Q8评论')
    reliability_q9_score = db.Column(db.Enum('0', '0.5', '1', name='reliability_score_enum'), default='1', nullable=True, comment='Q9得分')
    reliability_q9_comment = db.Column(db.Text, nullable=True, comment='Q9评论')
    reliability_q10_score = db.Column(db.Enum('0', '0.5', '1', name='reliability_score_enum'), default='1', nullable=True, comment='Q10得分')
    reliability_q10_comment = db.Column(db.Text, nullable=True, comment='Q10评论')
    reliability_total_score = db.Column(db.Numeric(4,1), nullable=True, comment='可靠性总得分 (0-10分)')
    
    # 相关性和风险强度
    correlation_score = db.Column(db.Enum('-1', '0', '1', name='correlation_score_enum'), default='1', nullable=True, comment='相关性得分')
    correlation_comment = db.Column(db.Text, nullable=True, comment='相关性评论')
    risk_intensity_score = db.Column(db.Enum('0.4', '0.8', '1', name='risk_intensity_enum'), default='1', nullable=True, comment='风险强度得分')
    risk_intensity_comment = db.Column(db.Text, nullable=True, comment='风险强度评论')
    
    # 元数据 
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # 关联关系
    literature = db.relationship('Literature', backref='epi_scorings')
    allergen_symptom = db.relationship('AllergenSymptom', backref='epi_scorings')

    __table_args__ = (
        db.Index('idx_epi_literature_id', 'literature_id'),
        db.Index('idx_epi_relation_id', 'relation_id'),
    )


class LiteratureVivoScoring(db.Model):
    """体内实验评分表"""
    __tablename__ = 'literature_vivo_scoring'

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True, comment='评分记录ID')
    literature_id = db.Column(db.BigInteger, db.ForeignKey('literature.id', ondelete='CASCADE'), nullable=False, comment='文献ID')
    relation_id = db.Column(db.BigInteger, db.ForeignKey('allergen_symptom.id', ondelete='SET NULL'), nullable=True, comment='关系ID')
    
    # 浓度权重 (Weight of Concentrations)
    type_of_model = db.Column(db.String(100), nullable=True, comment='模型类型')
    mode_of_exposure = db.Column(db.String(24), nullable=True, comment='暴露模式')
    dose = db.Column(db.Numeric(15,6), nullable=True, comment='剂量')
    dose_unit = db.Column(db.Enum('mg/kg/d', 'mg/L', name='dose_unit_enum'), default='mg/kg/d', comment='剂量单位')
    noael = db.Column(db.Numeric(15,6), nullable=True, comment='NOAEL值')
    conversion_factors = db.Column(db.Numeric(10,4), nullable=True, comment='转换因子')
    concentration_weight = db.Column(db.Numeric(3,2), nullable=True, comment='浓度权重得分 (0-1分)')
    
    # 可靠性得分 (0-10分)
    reliability_q1_score = db.Column(db.Enum('0', '0.5', '1', name='reliability_score_enum'), default='1', nullable=True, comment='Q1得分')
    reliability_q1_comment = db.Column(db.Text, nullable=True, comment='Q1评论')
    reliability_q2_score = db.Column(db.Enum('0', '0.5', '1', name='reliability_score_enum'), default='1', nullable=True, comment='Q2得分')
    reliability_q2_comment = db.Column(db.Text, nullable=True, comment='Q2评论')
    reliability_q3_score = db.Column(db.Enum('0', '0.5', '1', name='reliability_score_enum'), default='1', nullable=True, comment='Q3得分')
    reliability_q3_comment = db.Column(db.Text, nullable=True, comment='Q3评论')
    reliability_q4_score = db.Column(db.Enum('0', '0.5', '1', name='reliability_score_enum'), default='1', nullable=True, comment='Q4得分')
    reliability_q4_comment = db.Column(db.Text, nullable=True, comment='Q4评论')
    reliability_q5_score = db.Column(db.Enum('0', '0.5', '1', name='reliability_score_enum'), default='1', nullable=True, comment='Q5得分')
    reliability_q5_comment = db.Column(db.Text, nullable=True, comment='Q5评论')
    reliability_q6_score = db.Column(db.Enum('0', '0.5', '1', name='reliability_score_enum'), default='1', nullable=True, comment='Q6得分')
    reliability_q6_comment = db.Column(db.Text, nullable=True, comment='Q6评论')
    reliability_q7_score = db.Column(db.Enum('0', '0.5', '1', name='reliability_score_enum'), default='1', nullable=True, comment='Q7得分')
    reliability_q7_comment = db.Column(db.Text, nullable=True, comment='Q7评论')
    reliability_q8_score = db.Column(db.Enum('0', '0.5', '1', name='reliability_score_enum'), default='1', nullable=True, comment='Q8得分')
    reliability_q8_comment = db.Column(db.Text, nullable=True, comment='Q8评论')
    reliability_q9_score = db.Column(db.Enum('0', '0.5', '1', name='reliability_score_enum'), default='1', nullable=True, comment='Q9得分')
    reliability_q9_comment = db.Column(db.Text, nullable=True, comment='Q9评论')
    reliability_q10_score = db.Column(db.Enum('0', '0.5', '1', name='reliability_score_enum'), default='1', nullable=True, comment='Q10得分')
    reliability_q10_comment = db.Column(db.Text, nullable=True, comment='Q10评论')
    reliability_total_score = db.Column(db.Numeric(4,1), nullable=True, comment='可靠性总得分 (0-10分)')
    
    # 相关性和风险强度
    correlation_score = db.Column(db.Enum('-1', '0', '1', name='correlation_score_enum'), default='1', nullable=True, comment='相关性得分')
    correlation_comment = db.Column(db.Text, nullable=True, comment='相关性评论')
    risk_intensity_score = db.Column(db.Enum('0.4', '0.8', '1', name='risk_intensity_enum'), default='1', nullable=True, comment='风险强度得分')
    risk_intensity_comment = db.Column(db.Text, nullable=True, comment='风险强度评论')
    
    # 元数据 
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # 关联关系
    literature = db.relationship('Literature', backref='vivo_scorings')
    allergen_symptom = db.relationship('AllergenSymptom', backref='vivo_scorings')

    __table_args__ = (
        db.Index('idx_vivo_literature_id', 'literature_id'),
        db.Index('idx_vivo_relation_id', 'relation_id'),
    )


class LiteratureVitroScoring(db.Model):
    """体外实验评分表"""
    __tablename__ = 'literature_vitro_scoring'

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True, comment='评分记录ID')
    literature_id = db.Column(db.BigInteger, db.ForeignKey('literature.id', ondelete='CASCADE'), nullable=False, comment='文献ID')
    relation_id = db.Column(db.BigInteger, db.ForeignKey('allergen_symptom.id', ondelete='SET NULL'), nullable=True, comment='关系ID')
    
    # 浓度权重 (Weight of Concentrations)
    dose = db.Column(db.Numeric(15,6), nullable=True, comment='剂量')
    dose_unit = db.Column(db.String(20), default='mM', comment='剂量单位')
    molecular_weight = db.Column(db.Numeric(10,4), nullable=True, comment='分子量')
    concentration_weight = db.Column(db.Numeric(3,2), nullable=True, comment='浓度权重得分 (0-1分)')
    
    # 可靠性得分 (0-10分)
    reliability_q1_score = db.Column(db.Enum('0', '0.5', '1', name='reliability_score_enum'), default='1', nullable=True, comment='Q1得分')
    reliability_q1_comment = db.Column(db.Text, nullable=True, comment='Q1评论')
    reliability_q2_score = db.Column(db.Enum('0', '0.5', '1', name='reliability_score_enum'), default='1', nullable=True, comment='Q2得分')
    reliability_q2_comment = db.Column(db.Text, nullable=True, comment='Q2评论')
    reliability_q3_score = db.Column(db.Enum('0', '0.5', '1', name='reliability_score_enum'), default='1', nullable=True, comment='Q3得分')
    reliability_q3_comment = db.Column(db.Text, nullable=True, comment='Q3评论')
    reliability_q4_score = db.Column(db.Enum('0', '0.5', '1', name='reliability_score_enum'), default='1', nullable=True, comment='Q4得分')
    reliability_q4_comment = db.Column(db.Text, nullable=True, comment='Q4评论')
    reliability_q5_score = db.Column(db.Enum('0', '0.5', '1', name='reliability_score_enum'), default='1', nullable=True, comment='Q5得分')
    reliability_q5_comment = db.Column(db.Text, nullable=True, comment='Q5评论')
    reliability_q6_score = db.Column(db.Enum('0', '0.5', '1', name='reliability_score_enum'), default='1', nullable=True, comment='Q6得分')
    reliability_q6_comment = db.Column(db.Text, nullable=True, comment='Q6评论')
    reliability_q7_score = db.Column(db.Enum('0', '0.5', '1', name='reliability_score_enum'), default='1', nullable=True, comment='Q7得分')
    reliability_q7_comment = db.Column(db.Text, nullable=True, comment='Q7评论')
    reliability_q8_score = db.Column(db.Enum('0', '0.5', '1', name='reliability_score_enum'), default='1', nullable=True, comment='Q8得分')
    reliability_q8_comment = db.Column(db.Text, nullable=True, comment='Q8评论')
    reliability_q9_score = db.Column(db.Enum('0', '0.5', '1', name='reliability_score_enum'), default='1', nullable=True, comment='Q9得分')
    reliability_q9_comment = db.Column(db.Text, nullable=True, comment='Q9评论')
    reliability_q10_score = db.Column(db.Enum('0', '0.5', '1', name='reliability_score_enum'), default='1', nullable=True, comment='Q10得分')
    reliability_q10_comment = db.Column(db.Text, nullable=True, comment='Q10评论')
    reliability_total_score = db.Column(db.Numeric(4,1), nullable=True, comment='可靠性总得分 (0-10分)')
    
    # 相关性和风险强度
    correlation_score = db.Column(db.Enum('-1', '0', '1', name='correlation_score_enum'), default='1', nullable=True, comment='相关性得分')
    correlation_comment = db.Column(db.Text, nullable=True, comment='相关性评论')
    risk_intensity_score = db.Column(db.Enum('0.4', '0.8', '1', name='risk_intensity_enum'), default='1', nullable=True, comment='风险强度得分')
    risk_intensity_comment = db.Column(db.Text, nullable=True, comment='风险强度评论')
    
    # 元数据
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # 关联关系
    literature = db.relationship('Literature', backref='vitro_scorings')
    allergen_symptom = db.relationship('AllergenSymptom', backref='vitro_scorings')

    __table_args__ = (
        db.Index('idx_vitro_literature_id', 'literature_id'),
        db.Index('idx_vitro_relation_id', 'relation_id'),
    )
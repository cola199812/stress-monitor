import json
import chromadb
from sentence_transformers import SentenceTransformer
import os

# 固定绝对路径
base_dir = r"D:\stresor_data"
chroma_path = os.path.join(base_dir, "chroma_db")
model_path = os.path.join(base_dir, "models", "all-MiniLM-L6-v2")
json_path = os.path.join(base_dir, "data", "literature.json")

print(f"ChromaDB 路径: {chroma_path}")
print(f"模型路径: {model_path}")
print(f"JSON 路径: {json_path}")

# ✅ 初始化 Chroma 客户端
client = chromadb.PersistentClient(path=chroma_path)

# ✅ 删除旧集合（如果存在）
collection_name = "literature_collection"
try:
    client.delete_collection(name=collection_name)
    print("旧集合已删除")
except:
    print("集合不存在，将创建新集合")

# ✅ 创建新集合
collection = client.create_collection(name=collection_name)

# ✅ 加载模型
if not os.path.exists(model_path):
    raise FileNotFoundError(f"模型路径不存在: {model_path}")
model = SentenceTransformer(model_path)

# ✅ 读取 JSON 数据
if not os.path.exists(json_path):
    raise FileNotFoundError(f"JSON 文件不存在: {json_path}")
with open(json_path, "r", encoding="utf-8") as f:
    data = json.load(f)
print(f"读取到 {len(data)} 条数据")

# ✅ 批量生成向量
texts = [item["document"] for item in data]
embeddings = model.encode(texts).tolist()
print(f"共生成 {len(embeddings)} 个向量")

# ✅ 批量插入到 Chroma
ids = [item["id"] for item in data]
documents = [item["document"] for item in data]
metadatas = [item["metadata"] for item in data]

try:
    print("正在测试写入数据库...")
    collection.add(
        ids=ids,
        embeddings=embeddings,
        documents=documents,
        metadatas=metadatas
    )
    print("✅ 向量批量插入成功！")
except Exception as e:
    print(f"批量插入失败: {e}")
    print("尝试逐条插入...")
    for i, item in enumerate(data):
        try:
            collection.add(
                ids=[item["id"]],
                embeddings=[embeddings[i]],
                documents=[item["document"]],
                metadatas=[item["metadata"]]
            )
            print(f"第 {i+1} 条数据插入成功")
        except Exception as e2:
            print(f"第 {i+1} 条数据插入失败: {e2}")

print("✅ 向量数据库导入完成！")

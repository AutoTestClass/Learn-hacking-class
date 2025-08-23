from fastapi import FastAPI, Depends, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import text
from database import get_db, engine
import models
import pymysql
# import uvicorn
from loguru import logger

# 创建数据库表
models.Base.metadata.create_all(bind=engine)

app = FastAPI()

templates = Jinja2Templates(directory="templates")


# 初始化数据
@app.on_event("startup")
def init_data():
    db = next(get_db())
    # 检查用户表是否有数据
    if db.query(models.User).count() == 0:
        # 添加测试用户
        test_users = [
            models.User(username="admin", password="admin123", email="admin@example.com"),
            models.User(username="user1", password="password1", email="user1@example.com"),
            models.User(username="user2", password="password2", email="user2@example.com")
        ]
        db.add_all(test_users)

    # 检查产品表是否有数据
    if db.query(models.Product).count() == 0:
        # 添加测试产品
        test_products = [
            models.Product(name="笔记本电脑", price=5999, description="高性能笔记本电脑"),
            models.Product(name="智能手机", price=3999, description="最新款智能手机"),
            models.Product(name="平板电脑", price=2999, description="轻便平板电脑")
        ]
        db.add_all(test_products)

    db.commit()


# 首页
@app.get("/", response_class=HTMLResponse)
def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


# 1. 联合查询注入演示 (不安全)
@app.get("/union_injection/{product_id}")
def union_injection(product_id: str, db: Session = Depends(get_db)):
    # 不安全的查询方式 - 直接拼接用户输入
    query = f"SELECT id, name, price FROM products WHERE id = {product_id}"
    logger.debug(f"exe SQL: {query}")
    try:
        result = db.execute(text(query))
        # 将查询结果转换为字典列表
        products = [dict(row) for row in result.mappings()]
        return {"query": query, "results": products}
    except Exception as e:
        return {"error": str(e), "query": query}


# 3. 布尔盲注演示 (不安全)
@app.get("/boolean_blind/{input}")
def boolean_blind(input: str, db: Session = Depends(get_db)):
    # 不安全的查询方式
    query = f"SELECT username, email FROM users WHERE username = '{input}' "
    logger.debug(f"exe SQL: {query}")
    try:
        result = db.execute(text(query))
        # 将查询结果转换为字典列表
        products = [dict(row) for row in result.mappings()]
        return {"query": query, "results": products}
    except Exception as e:
        return {"error": str(e), "query": query}


# 4. 报错注入演示 (不安全)
@app.get("/error_injection/")
def error_injection(input: str, db: Session = Depends(get_db)):
    # 不安全的查询方式
    query = f"SELECT * FROM products WHERE id = {input}"
    logger.debug(f"exe SQL: {query}")
    try:
        result = db.execute(text(query))
        # 将查询结果转换为字典列表
        products = [dict(row) for row in result.mappings()]
        return {"query": query, "results": products}
    except Exception as e:
        return {"error": str(e), "query": query}


# 5. 时间盲注演示 (不安全)
@app.get("/time_blind/{input}")
def time_blind(input: str, db: Session = Depends(get_db)):
    # 不安全的查询方式
    query = f"SELECT * FROM products WHERE id = {input}"
    logger.debug(f"exe SQL: {query}")
    try:
        result = db.execute(text(query))
        # 将查询结果转换为字典列表
        products = [dict(row) for row in result.mappings()]
        return {"query": query, "results": products}
    except Exception as e:
        return {"error": str(e), "query": query}


# 6. 表单注入演示页面
@app.get("/form_injection", response_class=HTMLResponse)
def form_injection_page(request: Request):
    return templates.TemplateResponse("form_injection.html", {"request": request})


# 7. 表单注入处理 (不安全)
@app.post("/form_injection_submit")
def form_injection_submit(username: str = Form(...), db: Session = Depends(get_db)):
    # 不安全的查询方式
    query = f"SELECT * FROM users WHERE username = '{username}'"
    logger.debug(f"exe SQL: {query}")
    try:
        result = db.execute(text(query))
        # 将查询结果转换为字典列表
        users = [dict(row) for row in result.mappings()]
        return {"query": query, "results": users}
    except Exception as e:
        return {"error": str(e), "query": query}


# 8. 宽字节注入演示 (不安全)
@app.get("/wide_byte_injection/{input}")
def wide_byte_injection(input: str, db: Session = Depends(get_db)):
    # 模拟宽字节注入场景
    # 假设服务器使用GBK编码，并且会对单引号进行转义（添加反斜杠）
    escaped_input = input.replace("'", "\\'")
    # 宽字节注入会尝试用%df等字符吃掉反斜杠
    query = f"SELECT * FROM users WHERE username = '{escaped_input}'"
    logger.debug(f"exe SQL: {query}")
    try:
        result = db.execute(text(query))
        # 将查询结果转换为字典列表
        users = [dict(row) for row in result.mappings()]
        return {"query": query, "escaped_input": escaped_input, "results": users}
    except Exception as e:
        return {"error": str(e), "query": query, "escaped_input": escaped_input}


# 9. 堆叠查询注入演示 (不安全)
@app.get("/stacked_queries/{input}")
def stacked_queries(input: str, db: Session = Depends(get_db)):
    # 不安全的查询方式 - 允许执行多个查询
    query = f"SELECT * FROM products WHERE id = 1; {input}"
    logger.debug(f"exe SQL: {query}")
    try:
        # 注意：SQLAlchemy默认不允许堆叠查询，这里只是模拟演示
        # 在实际环境中，这可能需要使用其他方法来执行
        conn = engine.raw_connection()
        cursor = conn.cursor()
        cursor.execute(query)
        results = []
        while True:
            try:
                if cursor.description:
                    results.append(cursor.fetchall())
                cursor.nextset()
            except pymysql.err.ProgrammingError:
                break
        conn.close()
        return {"query": query, "results": results}
    except Exception as e:
        return {"error": str(e), "query": query}

# if __name__ == "__main__":
#     uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)

"""
Seed 测试数据脚本（阶段 3）

用途：向本地开发数据库预置商品、普通用户、管理员、订单。
重复运行不会插入重复数据（幂等）。
测试账号数据仅用于本地开发，严禁用于生产环境。

运行：
    cd D:\pyxuexi\langgraph\backend
    D:\pyxuexi\langgraph\.venv\Scripts\python.exe -m scripts.seed
"""

import sys
from datetime import datetime, timedelta

sys.path.insert(0, ".")

from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.order import AfterSalesStatus, Order, OrderStatus
from app.models.product import Product
from app.models.user import User, UserRole


def upsert_user(db: Session, username: str, password: str, role: UserRole) -> User:
    user = db.query(User).filter(User.username == username).first()
    if user:
        return user
    user = User(
        username=username,
        password_hash=hash_password(password),
        role=role,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    print(f"  用户 + {username} (role={role.value}, id={user.id})")
    return user


def upsert_product(
    db: Session, sku: str, name: str, category: str, description: str, price: float
) -> Product:
    product = db.query(Product).filter(Product.sku == sku).first()
    if product:
        return product
    product = Product(
        sku=sku,
        name=name,
        category=category,
        description=description,
        price=price,
        is_active=True,
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    print(f"  商品 + {name} (SKU={sku}, 价格={price}, id={product.id})")
    return product


def upsert_order(
    db: Session,
    order_no: str,
    user_id: int,
    product_id: int,
    quantity: int,
    unit_price: float,
    purchased_at: datetime,
    order_status: OrderStatus,
    after_sales_status: AfterSalesStatus,
) -> Order:
    order = db.query(Order).filter(Order.order_no == order_no).first()
    if order:
        return order
    order = Order(
        order_no=order_no,
        user_id=user_id,
        product_id=product_id,
        quantity=quantity,
        unit_price=unit_price,
        total_amount=round(unit_price * quantity, 2),
        order_status=order_status,
        purchased_at=purchased_at,
        after_sales_status=after_sales_status,
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    print(f"  订单 + {order_no} (用户={user_id}, 商品={product_id}, 金额={order.total_amount}, id={order.id})")
    return order


def main():
    print("=== Seed 测试数据开始 ===")
    db: Session = SessionLocal()

    try:
        # ---- 1. 用户 ----
        print("（1/3）创建用户...")
        users = {}
        users["alice"] = upsert_user(db, "alice", "seed123456", UserRole.user)
        users["bob"] = upsert_user(db, "bob", "seed123456", UserRole.user)
        users["admin"] = upsert_user(db, "admin", "admin123456", UserRole.admin)

        # ---- 2. 商品 ----
        print("（2/3）创建商品...")
        products = {}
        products["chocolate"] = upsert_product(
            db,
            sku="FOOD-001",
            name="手工黑巧克力礼盒 200g",
            category="食品",
            description="72%可可含量，独立包装，保质期6个月",
            price=68.00,
        )
        products["milk"] = upsert_product(
            db,
            sku="FOOD-002",
            name="有机纯牛奶 1L×12箱",
            category="食品",
            description="常温保存，每箱12盒，每盒1L",
            price=89.90,
        )
        products["earbuds"] = upsert_product(
            db,
            sku="TECH-001",
            name="主动降噪蓝牙耳机 Pro X",
            category="数码",
            description="蓝牙5.3，ANC降噪，单次续航8小时",
            price=1299.00,
        )
        products["phone_case"] = upsert_product(
            db,
            sku="TECH-002",
            name="硅胶保护壳 iPhone 15 Pro",
            category="数码配件",
            description="液态硅胶材质，精准开孔",
            price=39.00,
        )
        products["yoga_mat"] = upsert_product(
            db,
            sku="SPORT-001",
            name="加厚TPE瑜伽垫 10mm",
            category="运动",
            description="双面防滑，附赠收纳绑带",
            price=99.00,
        )

        # ---- 3. 订单 ----
        print("（3/3）创建订单...")
        now = datetime.utcnow()

        # alice 的订单
        upsert_order(
            db,
            order_no="ORD-20260901-001",
            user_id=users["alice"].id,
            product_id=products["chocolate"].id,
            quantity=2,
            unit_price=products["chocolate"].price,
            purchased_at=now - timedelta(days=20),
            order_status=OrderStatus.paid,
            after_sales_status=AfterSalesStatus.none,
        )
        upsert_order(
            db,
            order_no="ORD-20260910-001",
            user_id=users["alice"].id,
            product_id=products["earbuds"].id,
            quantity=1,
            unit_price=products["earbuds"].price,
            purchased_at=now - timedelta(days=5),
            order_status=OrderStatus.paid,
            after_sales_status=AfterSalesStatus.none,
        )

        # bob 的订单
        upsert_order(
            db,
            order_no="ORD-20260825-001",
            user_id=users["bob"].id,
            product_id=products["milk"].id,
            quantity=1,
            unit_price=products["milk"].price,
            purchased_at=now - timedelta(days=25),
            order_status=OrderStatus.paid,
            after_sales_status=AfterSalesStatus.refunded,
        )
        upsert_order(
            db,
            order_no="ORD-20260912-001",
            user_id=users["bob"].id,
            product_id=products["yoga_mat"].id,
            quantity=1,
            unit_price=products["yoga_mat"].price,
            purchased_at=now - timedelta(days=3),
            order_status=OrderStatus.paid,
            after_sales_status=AfterSalesStatus.none,
        )
        upsert_order(
            db,
            order_no="ORD-20260815-001",
            user_id=users["bob"].id,
            product_id=products["phone_case"].id,
            quantity=3,
            unit_price=products["phone_case"].price,
            purchased_at=now - timedelta(days=40),
            order_status=OrderStatus.paid,
            after_sales_status=AfterSalesStatus.returned,
        )

        # admin 没有订单（管理员不购物）

        print()
        print("=== Seed 完成 ===")
        print()
        print("【测试账号】")
        print("  普通用户  alice   / seed123456")
        print("  普通用户  bob     / seed123456")
        print("  管理员    admin   / admin123456")
        print()
        print("【测试商品】")
        for k, p in products.items():
            print(f"  {p.sku}  {p.name}  ¥{p.price:.2f}")
        print()
        print("【订单场景覆盖】")
        print("  alice: 巧克力(20天前,无售后) / 耳机(5天前,无售后)")
        print("  bob:   牛奶(25天前,已退款) / 瑜伽垫(3天前,无售后) / 手机壳(40天前,已退货)")
        print()
        print("⚠️  测试账号数据仅用于本地开发，严禁用于生产！")
        print("⚠️  重复运行本脚本不会插入重复数据（幂等）。")

    finally:
        db.close()


if __name__ == "__main__":
    main()
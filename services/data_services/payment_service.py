# -*- coding: utf-8 -*-
"""
医疗智能助手 - 支付数据服务
提供支付相关数据，包括订单、优惠券、发票等
"""

import json
import sqlite3
import asyncio
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime
from enum import Enum

try:
    import aiosqlite
    AIOSQLITE_AVAILABLE = True
except ImportError:
    AIOSQLITE_AVAILABLE = False


class OrderType(Enum):
    """订单类型"""
    APPOINTMENT = "appointment"  # 挂号
    CONSULTATION = "consultation"  # 问诊
    CHECKUP = "checkup"  # 体检
    MEDICATION = "medication"  # 药品
    OTHER = "other"


class OrderStatus(Enum):
    """订单状态"""
    PENDING = "pending"  # 待支付
    PAID = "paid"  # 已支付
    PROCESSING = "processing"  # 处理中
    COMPLETED = "completed"  # 已完成
    CANCELLED = "cancelled"  # 已取消
    REFUNDED = "refunded"  # 已退款
    EXPIRED = "expired"  # 已过期


class PaymentMethod(Enum):
    """支付方式"""
    WECHAT = "wechat"  # 微信支付
    ALIPAY = "alipay"  # 支付宝
    CARD = "card"  # 银行卡
    BALANCE = "balance"  # 余额
    INSURANCE = "insurance"  # 医保


class CouponType(Enum):
    """优惠券类型"""
    DISCOUNT = "discount"  # 折扣券
    AMOUNT = "amount"  # 满减券
    VOUCHER = "voucher"  # 代金券


class CouponStatus(Enum):
    """优惠券状态"""
    AVAILABLE = "available"  # 可用
    USED = "used"  # 已使用
    EXPIRED = "expired"  # 已过期


@dataclass
class Order:
    """订单"""
    order_id: str
    user_id: str
    order_type: str
    title: str
    description: Optional[str] = None
    amount: float = 0.0
    discount_amount: float = 0.0
    final_amount: float = 0.0
    currency: str = "CNY"
    status: str = OrderStatus.PENDING.value
    payment_method: Optional[str] = None
    transaction_id: Optional[str] = None
    paid_time: Optional[str] = None
    completed_time: Optional[str] = None
    cancelled_time: Optional[str] = None
    refund_amount: float = 0.0
    refunded_time: Optional[str] = None
    coupon_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "order_id": self.order_id,
            "user_id": self.user_id,
            "order_type": self.order_type,
            "title": self.title,
            "description": self.description,
            "amount": self.amount,
            "discount_amount": self.discount_amount,
            "final_amount": self.final_amount,
            "currency": self.currency,
            "status": self.status,
            "payment_method": self.payment_method,
            "transaction_id": self.transaction_id,
            "paid_time": self.paid_time,
            "completed_time": self.completed_time,
            "cancelled_time": self.cancelled_time,
            "refund_amount": self.refund_amount,
            "refunded_time": self.refunded_time,
            "coupon_id": self.coupon_id,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Order":
        """从字典创建"""
        return cls(**data)


@dataclass
class Coupon:
    """优惠券"""
    coupon_id: str
    user_id: str
    coupon_type: str
    title: str
    description: Optional[str] = None
    discount_value: float = 0.0  # 折扣值（百分比或金额）
    min_amount: float = 0.0  # 最低使用金额
    max_discount: float = 0.0  # 最大优惠金额
    status: str = CouponStatus.AVAILABLE.value
    valid_from: Optional[str] = None
    valid_until: Optional[str] = None
    used_time: Optional[str] = None
    used_order_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class Invoice:
    """发票"""
    invoice_id: str
    user_id: str
    order_id: str
    invoice_type: str  # individual, company
    invoice_title: str  # 发票抬头
    tax_number: Optional[str] = None  # 税号
    email: Optional[str] = None
    amount: float = 0.0
    status: str = "pending"  # pending, issued, failed
    invoice_url: Optional[str] = None
    issued_time: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


class PaymentService:
    """
    支付数据服务
    提供支付相关数据，包括订单、优惠券、发票等
    """

    def __init__(self, db_path: str = "data/payments.db"):
        """
        初始化支付服务

        Args:
            db_path: 数据库文件路径
        """
        self.db_path = db_path
        self._initialized = False
        self._cache: Dict[str, Order] = {}

        # 确保数据目录存在
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    def _get_schema_statements(self) -> List[str]:
        """获取数据库表结构SQL语句"""
        return [
            """CREATE TABLE IF NOT EXISTS orders (
                order_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                order_type TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                amount REAL NOT NULL DEFAULT 0,
                discount_amount REAL NOT NULL DEFAULT 0,
                final_amount REAL NOT NULL DEFAULT 0,
                currency TEXT NOT NULL DEFAULT 'CNY',
                status TEXT NOT NULL DEFAULT 'pending',
                payment_method TEXT,
                transaction_id TEXT,
                paid_time TEXT,
                completed_time TEXT,
                cancelled_time TEXT,
                refund_amount REAL NOT NULL DEFAULT 0,
                refunded_time TEXT,
                coupon_id TEXT,
                metadata TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )""",
            """CREATE TABLE IF NOT EXISTS coupons (
                coupon_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                coupon_type TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                discount_value REAL NOT NULL DEFAULT 0,
                min_amount REAL NOT NULL DEFAULT 0,
                max_discount REAL NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'available',
                valid_from TEXT,
                valid_until TEXT,
                used_time TEXT,
                used_order_id TEXT,
                metadata TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL
            )""",
            """CREATE TABLE IF NOT EXISTS invoices (
                invoice_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                order_id TEXT NOT NULL,
                invoice_type TEXT NOT NULL,
                invoice_title TEXT NOT NULL,
                tax_number TEXT,
                email TEXT,
                amount REAL NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'pending',
                invoice_url TEXT,
                issued_time TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (order_id) REFERENCES orders (order_id)
            )""",
            """CREATE INDEX IF NOT EXISTS idx_orders_user_id ON orders (user_id)""",
            """CREATE INDEX IF NOT EXISTS idx_orders_status ON orders (status)""",
            """CREATE INDEX IF NOT EXISTS idx_orders_created_at ON orders (created_at)""",
            """CREATE INDEX IF NOT EXISTS idx_coupons_user_id ON coupons (user_id)""",
            """CREATE INDEX IF NOT EXISTS idx_coupons_status ON coupons (status)""",
            """CREATE INDEX IF NOT EXISTS idx_invoices_user_id ON invoices (user_id)""",
            """CREATE INDEX IF NOT EXISTS idx_invoices_order_id ON invoices (order_id)""",
        ]

    async def initialize(self) -> None:
        """初始化数据库"""
        if self._initialized:
            return

        if AIOSQLITE_AVAILABLE:
            async with aiosqlite.connect(self.db_path) as db:
                for stmt in self._get_schema_statements():
                    await db.execute(stmt)
                await db.commit()
        else:
            self._initialize_sync()

        self._initialized = True

    def _initialize_sync(self) -> None:
        """同步初始化数据库"""
        with sqlite3.connect(self.db_path) as db:
            for stmt in self._get_schema_statements():
                db.execute(stmt)
            db.commit()
        self._initialized = True

    def _generate_order_id(self) -> str:
        """生成订单ID"""
        return f"ORD{datetime.now().strftime('%Y%m%d%H%M%S%f')[:22]}"

    def _generate_coupon_id(self) -> str:
        """生成优惠券ID"""
        return f"CPN{datetime.now().strftime('%Y%m%d%H%M%S%f')[:22]}"

    def _generate_invoice_id(self) -> str:
        """生成发票ID"""
        return f"INV{datetime.now().strftime('%Y%m%d%H%M%S%f')[:22]}"

    # ========== 订单操作 ==========

    async def create_order(
        self,
        user_id: str,
        order_type: str,
        title: str,
        amount: float,
        description: Optional[str] = None,
        coupon_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        创建订单

        Args:
            user_id: 用户ID
            order_type: 订单类型
            title: 标题
            amount: 金额
            description: 描述
            coupon_id: 优惠券ID
            metadata: 元数据

        Returns:
            Dict: 订单数据
        """
        await self.initialize()

        now = datetime.now().isoformat()

        # 计算优惠
        discount_amount = 0.0
        if coupon_id:
            coupon = await self.get_coupon(coupon_id)
            if coupon and coupon["status"] == CouponStatus.AVAILABLE.value:
                discount_amount = await self._calculate_discount(coupon, amount)

        final_amount = amount - discount_amount

        order = Order(
            order_id=self._generate_order_id(),
            user_id=user_id,
            order_type=order_type,
            title=title,
            description=description,
            amount=amount,
            discount_amount=discount_amount,
            final_amount=final_amount,
            coupon_id=coupon_id,
            metadata=metadata or {},
            created_at=now,
            updated_at=now
        )

        await self._save_order(order)
        self._cache[order.order_id] = order

        return order.to_dict()

    async def _calculate_discount(
        self,
        coupon: Dict[str, Any],
        amount: float
    ) -> float:
        """计算折扣金额"""
        discount_value = coupon.get("discount_value", 0)
        min_amount = coupon.get("min_amount", 0)
        max_discount = coupon.get("max_discount", 0)
        coupon_type = coupon.get("coupon_type", "")

        if amount < min_amount:
            return 0.0

        if coupon_type == CouponType.DISCOUNT.value:
            # 折扣券（百分比）
            discount = amount * (1 - discount_value / 100)
            if max_discount > 0:
                discount = min(discount, max_discount)
            return round(discount, 2)
        elif coupon_type == CouponType.AMOUNT.value:
            # 满减券
            return min(discount_value, max_discount) if max_discount > 0 else discount_value
        elif coupon_type == CouponType.VOUCHER.value:
            # 代金券
            return discount_value

        return 0.0

    async def _save_order(self, order: Order) -> None:
        """保存订单到数据库"""
        if AIOSQLITE_AVAILABLE:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT OR REPLACE INTO orders
                    (order_id, user_id, order_type, title, description,
                     amount, discount_amount, final_amount, currency,
                     status, payment_method, transaction_id, paid_time,
                     completed_time, cancelled_time, refund_amount, refunded_time,
                     coupon_id, metadata, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    order.order_id, order.user_id, order.order_type, order.title,
                    order.description, order.amount, order.discount_amount,
                    order.final_amount, order.currency, order.status,
                    order.payment_method, order.transaction_id, order.paid_time,
                    order.completed_time, order.cancelled_time, order.refund_amount,
                    order.refunded_time, order.coupon_id,
                    json.dumps(order.metadata, ensure_ascii=False),
                    order.created_at, order.updated_at
                ))
                await db.commit()
        else:
            with sqlite3.connect(self.db_path) as db:
                db.execute("""
                    INSERT OR REPLACE INTO orders
                    (order_id, user_id, order_type, title, description,
                     amount, discount_amount, final_amount, currency,
                     status, payment_method, transaction_id, paid_time,
                     completed_time, cancelled_time, refund_amount, refunded_time,
                     coupon_id, metadata, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    order.order_id, order.user_id, order.order_type, order.title,
                    order.description, order.amount, order.discount_amount,
                    order.final_amount, order.currency, order.status,
                    order.payment_method, order.transaction_id, order.paid_time,
                    order.completed_time, order.cancelled_time, order.refund_amount,
                    order.refunded_time, order.coupon_id,
                    json.dumps(order.metadata, ensure_ascii=False),
                    order.created_at, order.updated_at
                ))
                db.commit()

    def _load_order_from_row(self, row: tuple) -> Order:
        """从数据库行加载订单"""
        return Order(
            order_id=row[0],
            user_id=row[1],
            order_type=row[2],
            title=row[3],
            description=row[4],
            amount=row[5],
            discount_amount=row[6],
            final_amount=row[7],
            currency=row[8],
            status=row[9],
            payment_method=row[10],
            transaction_id=row[11],
            paid_time=row[12],
            completed_time=row[13],
            cancelled_time=row[14],
            refund_amount=row[15],
            refunded_time=row[16],
            coupon_id=row[17],
            metadata=json.loads(row[18]) if row[18] else {},
            created_at=row[19],
            updated_at=row[20]
        )

    async def get_order(self, order_id: str) -> Optional[Dict[str, Any]]:
        """获取订单"""
        await self.initialize()

        if order_id in self._cache:
            return self._cache[order_id].to_dict()

        if AIOSQLITE_AVAILABLE:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    "SELECT * FROM orders WHERE order_id = ?",
                    (order_id,)
                )
                row = await cursor.fetchone()
        else:
            with sqlite3.connect(self.db_path) as db:
                cursor = db.execute(
                    "SELECT * FROM orders WHERE order_id = ?",
                    (order_id,)
                )
                row = cursor.fetchone()

        if not row:
            return None

        order = self._load_order_from_row(row)
        self._cache[order_id] = order

        return order.to_dict()

    async def get_user_orders(
        self,
        user_id: str,
        status: Optional[str] = None,
        order_type: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """获取用户订单列表"""
        await self.initialize()

        query = "SELECT * FROM orders WHERE user_id = ?"
        params = [user_id]

        if status:
            query += " AND status = ?"
            params.append(status)

        if order_type:
            query += " AND order_type = ?"
            params.append(order_type)

        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        if AIOSQLITE_AVAILABLE:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(query, params)
                rows = await cursor.fetchall()
        else:
            with sqlite3.connect(self.db_path) as db:
                cursor = db.execute(query, params)
                rows = cursor.fetchall()

        return [self._load_order_from_row(row).to_dict() for row in rows]

    async def update_order_status(
        self,
        order_id: str,
        status: str,
        payment_method: Optional[str] = None,
        transaction_id: Optional[str] = None
    ) -> bool:
        """更新订单状态"""
        order_dict = await self.get_order(order_id)
        if not order_dict:
            return False

        order_dict["status"] = status
        order_dict["updated_at"] = datetime.now().isoformat()

        if payment_method:
            order_dict["payment_method"] = payment_method
        if transaction_id:
            order_dict["transaction_id"] = transaction_id

        if status == OrderStatus.PAID.value:
            order_dict["paid_time"] = datetime.now().isoformat()
        elif status == OrderStatus.COMPLETED.value:
            order_dict["completed_time"] = datetime.now().isoformat()
        elif status == OrderStatus.CANCELLED.value:
            order_dict["cancelled_time"] = datetime.now().isoformat()

        # 如果使用了优惠券，标记为已使用
        if status == OrderStatus.PAID.value and order_dict.get("coupon_id"):
            await self.use_coupon(order_dict["coupon_id"], order_id)

        order = Order.from_dict(order_dict)
        await self._save_order(order)
        self._cache[order_id] = order

        return True

    async def cancel_order(self, order_id: str) -> bool:
        """取消订单"""
        return await self.update_order_status(order_id, OrderStatus.CANCELLED.value)

    async def refund_order(
        self,
        order_id: str,
        refund_amount: Optional[float] = None
    ) -> bool:
        """退款"""
        order_dict = await self.get_order(order_id)
        if not order_dict:
            return False

        order_dict["status"] = OrderStatus.REFUNDED.value
        order_dict["refund_amount"] = refund_amount or order_dict["final_amount"]
        order_dict["refunded_time"] = datetime.now().isoformat()
        order_dict["updated_at"] = datetime.now().isoformat()

        order = Order.from_dict(order_dict)
        await self._save_order(order)
        self._cache[order_id] = order

        return True

    # ========== 优惠券操作 ==========

    async def create_coupon(
        self,
        user_id: str,
        coupon_type: str,
        title: str,
        discount_value: float,
        description: Optional[str] = None,
        min_amount: float = 0.0,
        max_discount: float = 0.0,
        valid_from: Optional[str] = None,
        valid_until: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """创建优惠券"""
        await self.initialize()

        coupon = Coupon(
            coupon_id=self._generate_coupon_id(),
            user_id=user_id,
            coupon_type=coupon_type,
            title=title,
            description=description,
            discount_value=discount_value,
            min_amount=min_amount,
            max_discount=max_discount,
            valid_from=valid_from,
            valid_until=valid_until,
            metadata=metadata or {}
        )

        if AIOSQLITE_AVAILABLE:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT INTO coupons
                    (coupon_id, user_id, coupon_type, title, description,
                     discount_value, min_amount, max_discount, status,
                     valid_from, valid_until, metadata, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    coupon.coupon_id, coupon.user_id, coupon.coupon_type,
                    coupon.title, coupon.description, coupon.discount_value,
                    coupon.min_amount, coupon.max_discount, coupon.status,
                    coupon.valid_from, coupon.valid_until,
                    json.dumps(coupon.metadata, ensure_ascii=False),
                    coupon.created_at
                ))
                await db.commit()
        else:
            with sqlite3.connect(self.db_path) as db:
                db.execute("""
                    INSERT INTO coupons
                    (coupon_id, user_id, coupon_type, title, description,
                     discount_value, min_amount, max_discount, status,
                     valid_from, valid_until, metadata, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    coupon.coupon_id, coupon.user_id, coupon.coupon_type,
                    coupon.title, coupon.description, coupon.discount_value,
                    coupon.min_amount, coupon.max_discount, coupon.status,
                    coupon.valid_from, valid_from, coupon.valid_until,
                    json.dumps(coupon.metadata, ensure_ascii=False),
                    coupon.created_at
                ))
                db.commit()

        return coupon.__dict__

    async def get_coupon(self, coupon_id: str) -> Optional[Dict[str, Any]]:
        """获取优惠券"""
        await self.initialize()

        if AIOSQLITE_AVAILABLE:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    "SELECT * FROM coupons WHERE coupon_id = ?",
                    (coupon_id,)
                )
                row = await cursor.fetchone()
        else:
            with sqlite3.connect(self.db_path) as db:
                cursor = db.execute(
                    "SELECT * FROM coupons WHERE coupon_id = ?",
                    (coupon_id,)
                )
                row = cursor.fetchone()

        if not row:
            return None

        return {
            "coupon_id": row[0],
            "user_id": row[1],
            "coupon_type": row[2],
            "title": row[3],
            "description": row[4],
            "discount_value": row[5],
            "min_amount": row[6],
            "max_discount": row[7],
            "status": row[8],
            "valid_from": row[9],
            "valid_until": row[10],
            "used_time": row[11],
            "used_order_id": row[12],
            "metadata": json.loads(row[13]) if row[13] else {},
            "created_at": row[14],
        }

    async def get_user_coupons(
        self,
        user_id: str,
        status: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """获取用户优惠券列表"""
        await self.initialize()

        query = "SELECT * FROM coupons WHERE user_id = ?"
        params = [user_id]

        if status:
            query += " AND status = ?"
            params.append(status)

        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        if AIOSQLITE_AVAILABLE:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(query, params)
                rows = await cursor.fetchall()
        else:
            with sqlite3.connect(self.db_path) as db:
                cursor = db.execute(query, params)
                rows = cursor.fetchall()

        return [
            {
                "coupon_id": row[0],
                "user_id": row[1],
                "coupon_type": row[2],
                "title": row[3],
                "description": row[4],
                "discount_value": row[5],
                "min_amount": row[6],
                "max_discount": row[7],
                "status": row[8],
                "valid_from": row[9],
                "valid_until": row[10],
                "used_time": row[11],
                "used_order_id": row[12],
                "metadata": json.loads(row[13]) if row[13] else {},
                "created_at": row[14],
            }
            for row in rows
        ]

    async def get_available_coupons(
        self,
        user_id: str,
        amount: float
    ) -> List[Dict[str, Any]]:
        """获取可用优惠券"""
        coupons = await self.get_user_coupons(user_id, status=CouponStatus.AVAILABLE.value)

        now = datetime.now().isoformat()
        available = []

        for coupon in coupons:
            # 检查有效期
            if coupon.get("valid_until") and coupon["valid_until"] < now:
                continue

            # 检查最低金额
            if amount < coupon.get("min_amount", 0):
                continue

            available.append(coupon)

        return available

    async def use_coupon(
        self,
        coupon_id: str,
        order_id: str
    ) -> bool:
        """使用优惠券"""
        await self.initialize()

        now = datetime.now().isoformat()

        if AIOSQLITE_AVAILABLE:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    UPDATE coupons
                    SET status = 'used', used_time = ?, used_order_id = ?
                    WHERE coupon_id = ?
                """, (now, order_id, coupon_id))
                await db.commit()
        else:
            with sqlite3.connect(self.db_path) as db:
                db.execute("""
                    UPDATE coupons
                    SET status = 'used', used_time = ?, used_order_id = ?
                    WHERE coupon_id = ?
                """, (now, order_id, coupon_id))
                db.commit()

        return True

    # ========== 发票操作 ==========

    async def create_invoice(
        self,
        user_id: str,
        order_id: str,
        invoice_type: str,
        invoice_title: str,
        tax_number: Optional[str] = None,
        email: Optional[str] = None
    ) -> Dict[str, Any]:
        """创建发票"""
        await self.initialize()

        # 获取订单金额
        order = await self.get_order(order_id)
        if not order:
            return {}

        invoice = Invoice(
            invoice_id=self._generate_invoice_id(),
            user_id=user_id,
            order_id=order_id,
            invoice_type=invoice_type,
            invoice_title=invoice_title,
            tax_number=tax_number,
            email=email,
            amount=order["final_amount"]
        )

        if AIOSQLITE_AVAILABLE:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT INTO invoices
                    (invoice_id, user_id, order_id, invoice_type,
                     invoice_title, tax_number, email, amount, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    invoice.invoice_id, invoice.user_id, invoice.order_id,
                    invoice.invoice_type, invoice.invoice_title,
                    invoice.tax_number, invoice.email, invoice.amount,
                    invoice.created_at
                ))
                await db.commit()
        else:
            with sqlite3.connect(self.db_path) as db:
                db.execute("""
                    INSERT INTO invoices
                    (invoice_id, user_id, order_id, invoice_type,
                     invoice_title, tax_number, email, amount, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    invoice.invoice_id, invoice.user_id, invoice.order_id,
                    invoice.invoice_type, invoice.invoice_title,
                    invoice.tax_number, invoice.email, invoice.amount,
                    invoice.created_at
                ))
                db.commit()

        return invoice.__dict__

    async def get_invoice(self, invoice_id: str) -> Optional[Dict[str, Any]]:
        """获取发票"""
        await self.initialize()

        if AIOSQLITE_AVAILABLE:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    "SELECT * FROM invoices WHERE invoice_id = ?",
                    (invoice_id,)
                )
                row = await cursor.fetchone()
        else:
            with sqlite3.connect(self.db_path) as db:
                cursor = db.execute(
                    "SELECT * FROM invoices WHERE invoice_id = ?",
                    (invoice_id,)
                )
                row = cursor.fetchone()

        if not row:
            return None

        return {
            "invoice_id": row[0],
            "user_id": row[1],
            "order_id": row[2],
            "invoice_type": row[3],
            "invoice_title": row[4],
            "tax_number": row[5],
            "email": row[6],
            "amount": row[7],
            "status": row[8],
            "invoice_url": row[9],
            "issued_time": row[10],
            "created_at": row[11],
        }

    async def get_user_invoices(
        self,
        user_id: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """获取用户发票列表"""
        await self.initialize()

        query = "SELECT * FROM invoices WHERE user_id = ? ORDER BY created_at DESC LIMIT ?"

        if AIOSQLITE_AVAILABLE:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(query, (user_id, limit))
                rows = await cursor.fetchall()
        else:
            with sqlite3.connect(self.db_path) as db:
                cursor = db.execute(query, (user_id, limit))
                rows = cursor.fetchall()

        return [
            {
                "invoice_id": row[0],
                "user_id": row[1],
                "order_id": row[2],
                "invoice_type": row[3],
                "invoice_title": row[4],
                "tax_number": row[5],
                "email": row[6],
                "amount": row[7],
                "status": row[8],
                "invoice_url": row[9],
                "issued_time": row[10],
                "created_at": row[11],
            }
            for row in rows
        ]

    async def update_invoice_status(
        self,
        invoice_id: str,
        status: str,
        invoice_url: Optional[str] = None
    ) -> bool:
        """更新发票状态"""
        await self.initialize()

        issued_time = datetime.now().isoformat() if status == "issued" else None

        if AIOSQLITE_AVAILABLE:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    UPDATE invoices
                    SET status = ?, invoice_url = ?, issued_time = ?
                    WHERE invoice_id = ?
                """, (status, invoice_url, issued_time, invoice_id))
                await db.commit()
        else:
            with sqlite3.connect(self.db_path) as db:
                db.execute("""
                    UPDATE invoices
                    SET status = ?, invoice_url = ?, issued_time = ?
                    WHERE invoice_id = ?
                """, (status, invoice_url, issued_time, invoice_id))
                db.commit()

        return True

    # ========== 统计信息 ==========

    async def get_stats(self) -> Dict[str, Any]:
        """获取服务统计信息"""
        await self.initialize()

        if AIOSQLITE_AVAILABLE:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute("SELECT COUNT(*) FROM orders")
                total_orders = (await cursor.fetchone())[0]

                cursor = await db.execute("SELECT COUNT(DISTINCT user_id) FROM orders")
                total_users = (await cursor.fetchone())[0]

                cursor = await db.execute("SELECT SUM(final_amount) FROM orders WHERE status = 'paid'")
                total_revenue = (await cursor.fetchone())[0] or 0

                cursor = await db.execute("SELECT COUNT(*) FROM coupons WHERE status = 'available'")
                active_coupons = (await cursor.fetchone())[0]
        else:
            with sqlite3.connect(self.db_path) as db:
                cursor = db.execute("SELECT COUNT(*) FROM orders")
                total_orders = cursor.fetchone()[0]

                cursor = db.execute("SELECT COUNT(DISTINCT user_id) FROM orders")
                total_users = cursor.fetchone()[0]

                cursor = db.execute("SELECT SUM(final_amount) FROM orders WHERE status = 'paid'")
                total_revenue = cursor.fetchone()[0] or 0

                cursor = db.execute("SELECT COUNT(*) FROM coupons WHERE status = 'available'")
                active_coupons = cursor.fetchone()[0]

        return {
            "total_orders": total_orders,
            "total_users": total_users,
            "total_revenue": round(total_revenue, 2),
            "active_coupons": active_coupons,
            "cache_size": len(self._cache),
        }


# ============================================================
# 全局服务实例
# ============================================================

_global_payment_service: Optional[PaymentService] = None


def get_payment_service(
    db_path: str = "data/payments.db"
) -> PaymentService:
    """获取全局支付服务"""
    global _global_payment_service
    if _global_payment_service is None:
        _global_payment_service = PaymentService(db_path)
    return _global_payment_service


def reset_payment_service():
    """重置全局支付服务"""
    global _global_payment_service
    _global_payment_service = None

# -*- coding: utf-8 -*-
"""
医疗智能助手 - 位置数据服务
提供位置相关服务，包括附近医院、药房、导航等
"""

import json
import sqlite3
import asyncio
import math
from typing import Optional, Dict, List, Any, Tuple
from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime
from enum import Enum

try:
    import aiosqlite
    AIOSQLITE_AVAILABLE = True
except ImportError:
    AIOSQLITE_AVAILABLE = False


class LocationType(Enum):
    """位置类型"""
    HOSPITAL = "hospital"  # 医院
    PHARMACY = "pharmacy"  # 药房
    CLINIC = "clinic"  # 诊所
    HEALTH_CENTER = "health_center"  # 卫生服务中心
    DIAGNOSTIC_CENTER = "diagnostic_center"  # 检查中心
    EMERGENCY = "emergency"  # 急救中心


class FacilityStatus(Enum):
    """机构状态"""
    OPEN = "open"  # 营业中
    CLOSED = "closed"  # 已关闭
    TEMPORARILY_CLOSED = "temporarily_closed"  # 暂时关闭


@dataclass
 class Location:
    """位置信息"""
    location_id: str
    name: str
    location_type: str
    address: str
    latitude: float
    longitude: float
    phone: Optional[str] = None
    status: str = FacilityStatus.OPEN.value
    opening_hours: Optional[str] = None
    departments: List[str] = field(default_factory=list)
    services: List[str] = field(default_factory=list)
    rating: Optional[float] = None
    review_count: int = 0
    features: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "location_id": self.location_id,
            "name": self.name,
            "location_type": self.location_type,
            "address": self.address,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "phone": self.phone,
            "status": self.status,
            "opening_hours": self.opening_hours,
            "departments": self.departments,
            "services": self.services,
            "rating": self.rating,
            "review_count": self.review_count,
            "features": self.features,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Location":
        """从字典创建"""
        return cls(**data)


@dataclass
class UserLocation:
    """用户位置"""
    user_id: str
    latitude: float
    longitude: float
    address: Optional[str] = None
    city: Optional[str] = None
    district: Optional[str] = None
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class NavigationRoute:
    """导航路线"""
    origin: Tuple[float, float]  # (latitude, longitude)
    destination: Tuple[float, float]
    distance: float  # 米
    duration: int  # 秒
    steps: List[Dict[str, Any]] = field(default_factory=list)
    mode: str = "driving"  # driving, walking, transit


class LocationService:
    """
    位置数据服务
    提供位置相关服务，包括附近医院、药房、导航等
    """

    def __init__(self, db_path: str = "data/locations.db"):
        """
        初始化位置服务

        Args:
            db_path: 数据库文件路径
        """
        self.db_path = db_path
        self._initialized = False
        self._location_cache: Dict[str, Location] = {}
        self._user_location_cache: Dict[str, UserLocation] = {}

        # 确保数据目录存在
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    def _get_schema_statements(self) -> List[str]:
        """获取数据库表结构SQL语句"""
        return [
            """CREATE TABLE IF NOT EXISTS locations (
                location_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                location_type TEXT NOT NULL,
                address TEXT NOT NULL,
                latitude REAL NOT NULL,
                longitude REAL NOT NULL,
                phone TEXT,
                status TEXT NOT NULL DEFAULT 'open',
                opening_hours TEXT,
                departments TEXT NOT NULL DEFAULT '[]',
                services TEXT NOT NULL DEFAULT '[]',
                rating REAL,
                review_count INTEGER NOT NULL DEFAULT 0,
                features TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )""",
            """CREATE TABLE IF NOT EXISTS user_locations (
                user_id TEXT PRIMARY KEY,
                latitude REAL NOT NULL,
                longitude REAL NOT NULL,
                address TEXT,
                city TEXT,
                district TEXT,
                updated_at TEXT NOT NULL
            )""",
            """CREATE INDEX IF NOT EXISTS idx_locations_type
                ON locations (location_type)""",
            """CREATE INDEX IF NOT EXISTS idx_locations_status
                ON locations (status)""",
            """CREATE VIRTUAL TABLE IF NOT EXISTS locations_fts USING fts5(
                name, address, departments
            )""",
        ]

    async def initialize(self) -> None:
        """初始化数据库"""
        if self._initialized:
            return

        if AIOSQLITE_AVAILABLE:
            async with aiosqlite.connect(self.db_path) as db:
                for stmt in self._get_schema_statements():
                    try:
                        await db.execute(stmt)
                    except Exception as e:
                        # FTS5可能不可用，忽略错误
                        if "fts5" not in str(e):
                            raise
                await db.commit()
        else:
            self._initialize_sync()

        self._initialized = True

    def _initialize_sync(self) -> None:
        """同步初始化数据库"""
        with sqlite3.connect(self.db_path) as db:
            for stmt in self._get_schema_statements():
                try:
                    db.execute(stmt)
                except Exception as e:
                    if "fts5" not in str(e):
                        raise
            db.commit()
        self._initialized = True

    def _generate_location_id(self) -> str:
        """生成位置ID"""
        return f"LOC{datetime.now().strftime('%Y%m%d%H%M%S%f')[:20]}"

    def _calculate_distance(
        self,
        lat1: float,
        lon1: float,
        lat2: float,
        lon2: float
    ) -> float:
        """
        计算两点间距离（Haversine公式）

        Args:
            lat1, lon1: 第一个点的纬度和经度
            lat2, lon2: 第二个点的纬度和经度

        Returns:
            float: 距离（米）
        """
        # 地球半径（米）
        R = 6371000

        # 转换为弧度
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)

        # Haversine公式
        a = (math.sin(delta_lat / 2) ** 2 +
             math.cos(lat1_rad) * math.cos(lat2_rad) *
             math.sin(delta_lon / 2) ** 2)
        c = 2 * math.asin(math.sqrt(a))

        return R * c

    async def _save_location(self, location: Location) -> None:
        """保存位置到数据库"""
        if AIOSQLITE_AVAILABLE:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT OR REPLACE INTO locations
                    (location_id, name, location_type, address, latitude, longitude,
                     phone, status, opening_hours, departments, services,
                     rating, review_count, features, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    location.location_id, location.name, location.location_type,
                    location.address, location.latitude, location.longitude,
                    location.phone, location.status, location.opening_hours,
                    json.dumps(location.departments, ensure_ascii=False),
                    json.dumps(location.services, ensure_ascii=False),
                    location.rating, location.review_count,
                    json.dumps(location.features, ensure_ascii=False),
                    location.created_at, location.updated_at
                ))
                await db.commit()
        else:
            with sqlite3.connect(self.db_path) as db:
                db.execute("""
                    INSERT OR REPLACE INTO locations
                    (location_id, name, location_type, address, latitude, longitude,
                     phone, status, opening_hours, departments, services,
                     rating, review_count, features, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    location.location_id, location.name, location.location_type,
                    location.address, location.latitude, location.longitude,
                    location.phone, location.status, location.opening_hours,
                    json.dumps(location.departments, ensure_ascii=False),
                    json.dumps(location.services, ensure_ascii=False),
                    location.rating, location.review_count,
                    json.dumps(location.features, ensure_ascii=False),
                    location.created_at, location.updated_at
                ))
                db.commit()

    def _load_location_from_row(self, row: tuple) -> Location:
        """从数据库行加载位置"""
        return Location(
            location_id=row[0],
            name=row[1],
            location_type=row[2],
            address=row[3],
            latitude=row[4],
            longitude=row[5],
            phone=row[6],
            status=row[7],
            opening_hours=row[8],
            departments=json.loads(row[9]) if row[9] else [],
            services=json.loads(row[10]) if row[10] else [],
            rating=row[11],
            review_count=row[12],
            features=json.loads(row[13]) if row[13] else {},
            created_at=row[14],
            updated_at=row[15]
        )

    # ========== 位置管理 ==========

    async def add_location(
        self,
        name: str,
        location_type: str,
        address: str,
        latitude: float,
        longitude: float,
        phone: Optional[str] = None,
        opening_hours: Optional[str] = None,
        departments: Optional[List[str]] = None,
        services: Optional[List[str]] = None,
        features: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        添加位置

        Args:
            name: 名称
            location_type: 位置类型
            address: 地址
            latitude: 纬度
            longitude: 经度
            phone: 电话
            opening_hours: 营业时间
            departments: 科室列表
            services: 服务列表
            features: 特性

        Returns:
            Dict: 位置数据
        """
        await self.initialize()

        now = datetime.now().isoformat()
        location = Location(
            location_id=self._generate_location_id(),
            name=name,
            location_type=location_type,
            address=address,
            latitude=latitude,
            longitude=longitude,
            phone=phone,
            opening_hours=opening_hours,
            departments=departments or [],
            services=services or [],
            features=features or {},
            created_at=now,
            updated_at=now
        )

        await self._save_location(location)
        self._location_cache[location.location_id] = location

        return location.to_dict()

    async def get_location(self, location_id: str) -> Optional[Dict[str, Any]]:
        """
        获取位置

        Args:
            location_id: 位置ID

        Returns:
            Optional[Dict]: 位置数据
        """
        await self.initialize()

        if location_id in self._location_cache:
            return self._location_cache[location_id].to_dict()

        if AIOSQLITE_AVAILABLE:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    "SELECT * FROM locations WHERE location_id = ?",
                    (location_id,)
                )
                row = await cursor.fetchone()
        else:
            with sqlite3.connect(self.db_path) as db:
                cursor = db.execute(
                    "SELECT * FROM locations WHERE location_id = ?",
                    (location_id,)
                )
                row = cursor.fetchone()

        if not row:
            return None

        location = self._load_location_from_row(row)
        self._location_cache[location_id] = location

        return location.to_dict()

    async def search_locations(
        self,
        keyword: str,
        location_type: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        搜索位置

        Args:
            keyword: 关键词
            location_type: 位置类型（可选）
            limit: 最大返回数量

        Returns:
            List[Dict]: 位置列表
        """
        await self.initialize()

        query = "SELECT * FROM locations WHERE status = 'open'"
        params = []

        if location_type:
            query += " AND location_type = ?"
            params.append(location_type)

        # 模糊搜索
        query += " AND (name LIKE ? OR address LIKE ?)"
        params.extend([f"%{keyword}%", f"%{keyword}%"])

        query += " LIMIT ?"
        params.append(limit)

        if AIOSQLITE_AVAILABLE:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(query, params)
                rows = await cursor.fetchall()
        else:
            with sqlite3.connect(self.db_path) as db:
                cursor = db.execute(query, params)
                rows = cursor.fetchall()

        return [self._load_location_from_row(row).to_dict() for row in rows]

    # ========== 附近查询 ==========

    async def find_nearby(
        self,
        latitude: float,
        longitude: float,
        location_type: Optional[str] = None,
        radius: float = 5000,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        查找附近位置

        Args:
            latitude: 纬度
            longitude: 经度
            location_type: 位置类型（可选）
            radius: 半径（米）
            limit: 最大返回数量

        Returns:
            List[Dict]: 附近位置列表
        """
        await self.initialize()

        # 获取所有候选位置
        query = "SELECT * FROM locations WHERE status = 'open'"
        params = []

        if location_type:
            query += " AND location_type = ?"
            params.append(location_type)

        if AIOSQLITE_AVAILABLE:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(query, params)
                rows = await cursor.fetchall()
        else:
            with sqlite3.connect(self.db_path) as db:
                cursor = db.execute(query, params)
                rows = cursor.fetchall()

        # 计算距离并筛选
        results = []
        for row in rows:
            location = self._load_location_from_row(row)
            distance = self._calculate_distance(
                latitude, longitude,
                location.latitude, location.longitude
            )

            if distance <= radius:
                location_dict = location.to_dict()
                location_dict["distance"] = round(distance, 2)
                results.append(location_dict)

        # 按距离排序
        results.sort(key=lambda x: x["distance"])

        return results[:limit]

    async def find_nearby_hospitals(
        self,
        latitude: float,
        longitude: float,
        radius: float = 10000,
        department: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        查找附近医院

        Args:
            latitude: 纬度
            longitude: 经度
            radius: 半径（米）
            department: 科室筛选（可选）

        Returns:
            List[Dict]: 附近医院列表
        """
        hospitals = await self.find_nearby(
            latitude, longitude,
            location_type=LocationType.HOSPITAL.value,
            radius=radius
        )

        if department:
            # 筛选有指定科室的医院
            hospitals = [
                h for h in hospitals
                if department in h.get("departments", [])
            ]

        return hospitals

    async def find_nearby_pharmacies(
        self,
        latitude: float,
        longitude: float,
        radius: float = 3000
    ) -> List[Dict[str, Any]]:
        """
        查找附近药房

        Args:
            latitude: 纬度
            longitude: 经度
            radius: 半径（米）

        Returns:
            List[Dict]: 附近药房列表
        """
        return await self.find_nearby(
            latitude, longitude,
            location_type=LocationType.PHARMACY.value,
            radius=radius
        )

    async def find_nearest_emergency(
        self,
        latitude: float,
        longitude: float
    ) -> Optional[Dict[str, Any]]:
        """
        查找最近的急救中心

        Args:
            latitude: 纬度
            longitude: 经度

        Returns:
            Optional[Dict]: 最近的急救中心
        """
        results = await self.find_nearby(
            latitude, longitude,
            location_type=LocationType.EMERGENCY.value,
            radius=50000,  # 50km范围内
            limit=1
        )

        return results[0] if results else None

    # ========== 用户位置 ==========

    async def update_user_location(
        self,
        user_id: str,
        latitude: float,
        longitude: float,
        address: Optional[str] = None,
        city: Optional[str] = None,
        district: Optional[str] = None
    ) -> bool:
        """
        更新用户位置

        Args:
            user_id: 用户ID
            latitude: 纬度
            longitude: 经度
            address: 地址
            city: 城市
            district: 区县

        Returns:
            bool: 是否更新成功
        """
        await self.initialize()

        now = datetime.now().isoformat()

        user_location = UserLocation(
            user_id=user_id,
            latitude=latitude,
            longitude=longitude,
            address=address,
            city=city,
            district=district,
            updated_at=now
        )

        self._user_location_cache[user_id] = user_location

        if AIOSQLITE_AVAILABLE:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT OR REPLACE INTO user_locations
                    (user_id, latitude, longitude, address, city, district, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    user_id, latitude, longitude, address, city, district, now
                ))
                await db.commit()
        else:
            with sqlite3.connect(self.db_path) as db:
                db.execute("""
                    INSERT OR REPLACE INTO user_locations
                    (user_id, latitude, longitude, address, city, district, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    user_id, latitude, longitude, address, city, district, now
                ))
                db.commit()

        return True

    async def get_user_location(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        获取用户位置

        Args:
            user_id: 用户ID

        Returns:
            Optional[Dict]: 用户位置
        """
        await self.initialize()

        if user_id in self._user_location_cache:
            ul = self._user_location_cache[user_id]
            return {
                "user_id": ul.user_id,
                "latitude": ul.latitude,
                "longitude": ul.longitude,
                "address": ul.address,
                "city": ul.city,
                "district": ul.district,
                "updated_at": ul.updated_at,
            }

        if AIOSQLITE_AVAILABLE:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    "SELECT * FROM user_locations WHERE user_id = ?",
                    (user_id,)
                )
                row = await cursor.fetchone()
        else:
            with sqlite3.connect(self.db_path) as db:
                cursor = db.execute(
                    "SELECT * FROM user_locations WHERE user_id = ?",
                    (user_id,)
                )
                row = cursor.fetchone()

        if not row:
            return None

        return {
            "user_id": row[0],
            "latitude": row[1],
            "longitude": row[2],
            "address": row[3],
            "city": row[4],
            "district": row[5],
            "updated_at": row[6],
        }

    async def find_nearby_for_user(
        self,
        user_id: str,
        location_type: Optional[str] = None,
        radius: float = 5000,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        查找用户附近的位置

        Args:
            user_id: 用户ID
            location_type: 位置类型
            radius: 半径（米）
            limit: 最大返回数量

        Returns:
            List[Dict]: 附近位置列表
        """
        user_location = await self.get_user_location(user_id)
        if not user_location:
            return []

        return await self.find_nearby(
            user_location["latitude"],
            user_location["longitude"],
            location_type=location_type,
            radius=radius,
            limit=limit
        )

    # ========== 导航 ==========

    async def calculate_distance(
        self,
        origin: Tuple[float, float],
        destination: Tuple[float, float]
    ) -> float:
        """
        计算两点间距离

        Args:
            origin: 起点 (latitude, longitude)
            destination: 终点 (latitude, longitude)

        Returns:
            float: 距离（米）
        """
        return self._calculate_distance(
            origin[0], origin[1],
            destination[0], destination[1]
        )

    async def get_navigation_route(
        self,
        origin: Tuple[float, float],
        destination: Tuple[float, float],
        mode: str = "driving"
    ) -> NavigationRoute:
        """
        获取导航路线（简化版）

        Args:
            origin: 起点
            destination: 终点
            mode: 出行方式

        Returns:
            NavigationRoute: 导航路线
        """
        distance = await self.calculate_distance(origin, destination)

        # 估算时间（简化计算）
        speed_map = {
            "driving": 15,  # m/s (约54km/h)
            "walking": 1.4,  # m/s (约5km/h)
            "transit": 8,  # m/s (约29km/h)
        }
        speed = speed_map.get(mode, 15)
        duration = int(distance / speed)

        return NavigationRoute(
            origin=origin,
            destination=destination,
            distance=distance,
            duration=duration,
            mode=mode
        )

    async def get_navigation_to_location(
        self,
        user_id: str,
        location_id: str,
        mode: str = "driving"
    ) -> Optional[Dict[str, Any]]:
        """
        获取到指定位置的导航

        Args:
            user_id: 用户ID
            location_id: 目标位置ID
            mode: 出行方式

        Returns:
            Optional[Dict]: 导航信息
        """
        user_location = await self.get_user_location(user_id)
        if not user_location:
            return None

        target_location = await self.get_location(location_id)
        if not target_location:
            return None

        route = await self.get_navigation_route(
            (user_location["latitude"], user_location["longitude"]),
            (target_location["latitude"], target_location["longitude"]),
            mode
        )

        return {
            "origin": user_location,
            "destination": target_location,
            "distance": route.distance,
            "duration": route.duration,
            "mode": route.mode,
            "destination_name": target_location["name"],
            "destination_address": target_location["address"],
        }

    # ========== 数据管理 ==========

    async def update_location(
        self,
        location_id: str,
        data: Dict[str, Any]
    ) -> bool:
        """
        更新位置信息

        Args:
            location_id: 位置ID
            data: 更新数据

        Returns:
            bool: 是否更新成功
        """
        location_dict = await self.get_location(location_id)
        if not location_dict:
            return False

        updatable_fields = [
            "name", "location_type", "address", "latitude", "longitude",
            "phone", "status", "opening_hours", "rating", "review_count"
        ]

        for field in updatable_fields:
            if field in data:
                location_dict[field] = data[field]

        if "departments" in data:
            location_dict["departments"] = data["departments"]

        if "services" in data:
            location_dict["services"] = data["services"]

        if "features" in data:
            location_dict["features"].update(data["features"])

        location_dict["updated_at"] = datetime.now().isoformat()

        location = Location.from_dict(location_dict)
        await self._save_location(location)
        self._location_cache[location_id] = location

        return True

    async def delete_location(self, location_id: str) -> bool:
        """
        删除位置

        Args:
            location_id: 位置ID

        Returns:
            bool: 是否删除成功
        """
        await self.initialize()

        if AIOSQLITE_AVAILABLE:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    "DELETE FROM locations WHERE location_id = ?",
                    (location_id,)
                )
                await db.commit()
                deleted = cursor.rowcount > 0
        else:
            with sqlite3.connect(self.db_path) as db:
                cursor = db.execute(
                    "DELETE FROM locations WHERE location_id = ?",
                    (location_id,)
                )
                db.commit()
                deleted = cursor.rowcount > 0

        if deleted and location_id in self._location_cache:
            del self._location_cache[location_id]

        return deleted

    # ========== 统计信息 ==========

    async def get_stats(self) -> Dict[str, Any]:
        """
        获取服务统计信息

        Returns:
            Dict: 统计信息
        """
        await self.initialize()

        if AIOSQLITE_AVAILABLE:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute("SELECT COUNT(*) FROM locations")
                total_locations = (await cursor.fetchone())[0]

                cursor = await db.execute("""
                    SELECT location_type, COUNT(*) as count
                    FROM locations
                    GROUP BY location_type
                """)
                type_counts = {row[0]: row[1] for row in await cursor.fetchall()}
        else:
            with sqlite3.connect(self.db_path) as db:
                cursor = db.execute("SELECT COUNT(*) FROM locations")
                total_locations = cursor.fetchone()[0]

                cursor = db.execute("""
                    SELECT location_type, COUNT(*) as count
                    FROM locations
                    GROUP BY location_type
                """)
                type_counts = {row[0]: row[1] for row in cursor.fetchall()}

        return {
            "total_locations": total_locations,
            "type_counts": type_counts,
            "location_cache_size": len(self._location_cache),
            "user_location_cache_size": len(self._user_location_cache),
        }


# ============================================================
# 全局服务实例
# ============================================================

_global_location_service: Optional[LocationService] = None


def get_location_service(
    db_path: str = "data/locations.db"
) -> LocationService:
    """获取全局位置服务"""
    global _global_location_service
    if _global_location_service is None:
        _global_location_service = LocationService(db_path)
    return _global_location_service


def reset_location_service():
    """重置全局位置服务"""
    global _global_location_service
    _global_location_service = None

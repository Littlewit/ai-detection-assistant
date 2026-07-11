"""AI检测助手 - 全局配置管理"""

from pydantic_settings import BaseSettings
from functools import lru_cache
import os


class Settings(BaseSettings):
    """应用配置，从 .env 文件和环境变量加载"""

    # 千问大模型
    dashscope_api_key: str = ""
    qwen_text_model: str = "qwen-max"
    qwen_vl_model: str = "qwen-vl-max"
    qwen_embedding_model: str = "text-embedding-v3"

    # 向量数据库
    chroma_persist_dir: str = "./data/chroma_db"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # 实验室资质
    lab_cnas_id: str = "L7462"
    lab_cma_id: str = "2016192581Z"
    lab_cpsc_id: str = "1517"

    # 应用
    app_host: str = "0.0.0.0"
    app_port: int = 8888
    log_level: str = "info"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """获取配置单例"""
    return Settings()


# 标准体系分区
STANDARD_CATEGORIES = {
    "chemical": "有害物质检测 (RoHS/REACH/CPSIA/加州65/POPs等)",
    "safety": "安规检测 (IEC/EN/UL/GB 电气安全)",
    "emc": "电磁兼容检测 (EMI/EMS/FCC Part 15等)",
    "reliability": "环境可靠性 (温湿度/盐雾/振动/老化)",
    "material": "材料分析 (金属/非金属/REACH SVHC)",
    "textile": "纺织品/鞋类/皮革 (GB/T/ISO/AATCC)",
    "toy": "玩具检测 (EN71/ASTM F963/GB 6675)",
    "food_contact": "食品接触材料 (FDA/EU 10/2011/GB 4806)",
    "energy": "能效检测 (ErP/Energy Star)",
    "certification": "认证流程 (CE/FCC/UL/CB/CCC等)",
}

# 数据目录
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
STANDARDS_DIR = os.path.join(DATA_DIR, "standards")
REPORTS_DIR = os.path.join(DATA_DIR, "reports")
UPLOADS_DIR = os.path.join(DATA_DIR, "uploads")
TEMPLATES_DIR = os.path.join(DATA_DIR, "templates")

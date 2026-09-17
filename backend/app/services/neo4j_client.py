from __future__ import annotations

import os
from typing import Optional

from neo4j import GraphDatabase, Driver
from dotenv import load_dotenv


class Neo4jClient:
    _driver: Optional[Driver] = None

    @classmethod
    def init_driver(cls) -> Driver:
        if cls._driver is not None:
            return cls._driver

        load_dotenv()
        uri = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
        user = os.getenv('NEO4J_USER', 'neo4j')
        password = os.getenv('NEO4J_PASSWORD', '123456789')
        encrypted = os.getenv('NEO4J_ENCRYPTED', 'false').lower() == 'true'

        auth = (user, password)
        cls._driver = GraphDatabase.driver(uri, auth=auth, encrypted=encrypted)
        return cls._driver

    @classmethod
    def get_driver(cls) -> Driver:
        return cls.init_driver()

    @classmethod
    def close(cls) -> None:
        if cls._driver is not None:
            cls._driver.close()
            cls._driver = None


def health_check() -> bool:
    try:
        driver = Neo4jClient.get_driver()
        with driver.session() as session:
            value = session.run('RETURN 1 AS ok').single()
            return bool(value and value['ok'] == 1)
    except Exception:
        return False



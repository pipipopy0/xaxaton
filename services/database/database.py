from typing import Any, Dict, List, Optional, Tuple
import psycopg2
from psycopg2 import sql
from psycopg2.extensions import connection as PsycopgConnection
from logger_config import logger


class Database:
    """
    Обёртка над psycopg2 для безопасной работы с PostgreSQL.
    С автоматическим переподключением при обрыве соединения.
    """

    def __init__(self, connection: PsycopgConnection) -> None:
        """
        :param connection: активное соединение с БД.
        """
        self.connection = connection
        # Сохраняем параметры для переподключения
        dsn = connection.get_dsn_parameters()
        self.conn_params = {
            "host": dsn.get("host"),
            "port": dsn.get("port"),
            "dbname": dsn.get("dbname"),
            "user": dsn.get("user"),
            "password": dsn.get("password"),
        }
        # Убираем None значения
        self.conn_params = {k: v for k, v in self.conn_params.items() if v is not None}

    def _ensure_connection(self) -> None:
        """
        Проверяет, живо ли соединение, и пересоздаёт при необходимости.
        """
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("SELECT 1")
        except (psycopg2.InterfaceError, psycopg2.OperationalError, AttributeError):
            logger.warning("Database connection lost, reconnecting...")
            try:
                self.connection = psycopg2.connect(**self.conn_params)
                logger.info("Database reconnected successfully")
            except Exception as e:
                logger.error(f"Failed to reconnect to database: {e}")
                raise

    def _safe_rollback(self) -> None:
        """
        Безопасный rollback — не падает, если соединение уже закрыто.
        """
        try:
            self.connection.rollback()
        except Exception:
            pass

    def create_table(self, tables: Dict[str, str]) -> None:
        """
        Создаёт таблицы, если их нет.
        :param tables: словарь {имя_таблицы: определение_колонок}
        """
        self._ensure_connection()
        try:
            with self.connection.cursor() as cursor:
                for table_name, columns_def in tables.items():
                    query = sql.SQL("CREATE TABLE IF NOT EXISTS {} ({})").format(
                        sql.Identifier(table_name),
                        sql.SQL(columns_def)
                    )
                    cursor.execute(query)
                    logger.info(f"Table '{table_name}' ensured")
                self.connection.commit()
        except Exception as e:
            self._safe_rollback()
            logger.error(f"Ошибка в create_table: {e}")
            raise e

    def insert_data(
        self,
        table_name: str,
        data: Dict[str, Any],
        returning_col: Optional[str] = "id"
    ) -> Optional[Any]:
        """
        Вставляет одну строку.
        :param returning_col: колонка, значение которой вернуть (или None, чтобы не возвращать).
        :return: значение returning_col или None.
        """
        self._ensure_connection()

        if not data:
            raise ValueError("Cannot insert empty data")

        columns = list(data.keys())
        values = list(data.values())

        columns_sql = sql.SQL(", ").join(map(sql.Identifier, columns))
        placeholders = sql.SQL(", ").join([sql.Placeholder()] * len(values))

        if returning_col:
            query = sql.SQL(
                "INSERT INTO {} ({}) VALUES ({}) RETURNING {}"
            ).format(
                sql.Identifier(table_name),
                columns_sql,
                placeholders,
                sql.Identifier(returning_col)
            )
        else:
            query = sql.SQL(
                "INSERT INTO {} ({}) VALUES ({})"
            ).format(
                sql.Identifier(table_name),
                columns_sql,
                placeholders
            )

        try:
            with self.connection.cursor() as cursor:
                cursor.execute(query, values)
                self.connection.commit()
                if returning_col:
                    row = cursor.fetchone()
                    return row[0] if row else None
                return None
        except Exception as e:
            self._safe_rollback()
            logger.error(f"Ошибка в insert_data: {e}")
            raise e

    def update_data(
        self,
        table_name: str,
        data: Dict[str, Any],
        where_conditions: Dict[str, Any],
        where_operator: str = "AND"
    ) -> int:
        """
        Обновляет строки по условиям.
        :return: количество обновлённых строк.
        """
        self._ensure_connection()

        if not data:
            raise ValueError("No data to update")
        if not where_conditions:
            raise ValueError("WHERE conditions cannot be empty")

        set_parts = [
            sql.SQL("{} = {}").format(sql.Identifier(col), sql.Placeholder())
            for col in data.keys()
        ]
        set_sql = sql.SQL(", ").join(set_parts)

        where_parts = [
            sql.SQL("{} = {}").format(sql.Identifier(col), sql.Placeholder())
            for col in where_conditions.keys()
        ]
        where_sql = sql.SQL(" " + where_operator + " ").join(where_parts)

        query = sql.SQL("UPDATE {} SET {} WHERE {}").format(
            sql.Identifier(table_name),
            set_sql,
            where_sql
        )

        params = list(data.values()) + list(where_conditions.values())

        try:
            with self.connection.cursor() as cursor:
                cursor.execute(query, params)
                self.connection.commit()
                return cursor.rowcount
        except Exception as e:
            self._safe_rollback()
            logger.error(f"Ошибка в update_data: {e}")
            raise e

    def select_data(
        self,
        table_name: str,
        columns: Optional[List[str]] = None,
        where_conditions: Optional[Dict[str, Any]] = None,
        where_operator: str = "AND"
    ) -> List[Tuple]:
        """
        Выбирает данные из таблицы.
        """
        self._ensure_connection()

        if columns is None:
            columns_sql = sql.SQL("*")
        else:
            columns_sql = sql.SQL(", ").join(map(sql.Identifier, columns))

        if where_conditions:
            where_parts = [
                sql.SQL("{} = {}").format(sql.Identifier(col), sql.Placeholder())
                for col in where_conditions.keys()
            ]
            where_sql = sql.SQL(" WHERE {}").format(
                sql.SQL(" " + where_operator + " ").join(where_parts)
            )
            params = list(where_conditions.values())
        else:
            where_sql = sql.SQL("")
            params = []

        query = sql.SQL("SELECT {} FROM {}{}").format(
            columns_sql,
            sql.Identifier(table_name),
            where_sql
        )

        try:
            with self.connection.cursor() as cursor:
                cursor.execute(query, params)
                return cursor.fetchall()
        except Exception as e:
            self._safe_rollback()
            logger.error(f"Ошибка в select_data: {e}")
            raise e

    def delete_data(
        self,
        table_name: str,
        where_conditions: Dict[str, Any],
        where_operator: str = "AND"
    ) -> int:
        """
        Удаляет строки по условиям.
        :return: количество удалённых строк.
        """
        self._ensure_connection()

        if not where_conditions:
            raise ValueError("WHERE conditions cannot be empty – use TRUNCATE if needed")

        where_parts = [
            sql.SQL("{} = {}").format(sql.Identifier(col), sql.Placeholder())
            for col in where_conditions.keys()
        ]
        where_sql = sql.SQL(" " + where_operator + " ").join(where_parts)

        query = sql.SQL("DELETE FROM {} WHERE {}").format(
            sql.Identifier(table_name),
            where_sql
        )

        params = list(where_conditions.values())

        try:
            with self.connection.cursor() as cursor:
                cursor.execute(query, params)
                self.connection.commit()
                return cursor.rowcount
        except Exception as e:
            self._safe_rollback()
            logger.error(f"Ошибка в delete_data: {e}")
            raise e
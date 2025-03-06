from sqlalchemy.orm import Session
from sqlalchemy import text
import logging

logger = logging.getLogger(__name__)

class StorageRepository:
    """
    Repository for storing and retrieving data in the storage database.
    """
    @staticmethod
    async def insert_csv(db: Session, table_name: str, create_table_query: str, columns: list[str], data: list[dict]):
        """
        Insert CSV data into the storage database.
        """
        logger.info(f"Inserting CSV data into {table_name} with {len(data)} rows and {len(create_table_query)} columns")
        try:
            # create a table if it doesn't exist
            logger.info(f"Create Table Query: {create_table_query}")
            db.execute(text(create_table_query))
            logger.info(f"Successfully created table {table_name}")

            # insert the data one by one 
            for row in data:
                INSERT_ROW_QUERY = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({', '.join([f"'{str(cell)}'" for cell in row])})"
                logger.info(f"Insert Row Query: {INSERT_ROW_QUERY}")
                db.execute(text(INSERT_ROW_QUERY))
            db.commit()
            logger.info(f"Successfully inserted CSV data into {table_name}")
            return True
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to insert data into {table_name}: {e}")
            raise

    @staticmethod
    async def query(db: Session, query: str):
        try:
            return db.execute(text(query)).fetchall()
        except Exception as e:
            logger.error(f"Failed to query data: {e}")
            raise
        
        
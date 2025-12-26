from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import mysql.connector

SQLALCHEMY_DATABASE_URL = "mysql+mysqlconnector://root:1234@localhost:3306/cat_db"

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def init_db():
    try:
        # Use raw connector to ensure database matches connection string if needed, 
        # or simply rely on SQLAlchemy create_all if the DB exists.
        # For safety/completeness based on previous logic:
        connection = mysql.connector.connect(
            host="localhost",
            port=3306,
            user="root",
            password="1234",
            database="cat_db"
        )
        if connection.is_connected():
            cursor = connection.cursor()
            # Explicitly checking/creating tables might be handled by migration tools in production,
            # but we keep the robust raw query approach from the previous setup to ensure they exist.
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS cat_captures (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    image_path VARCHAR(255) NOT NULL,
                    score FLOAT NOT NULL,
                    created_at DATETIME NOT NULL
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    email VARCHAR(255) UNIQUE NOT NULL,
                    password VARCHAR(255) NOT NULL
                )
            """)
            connection.commit()
            print("[MySQL] Database tables checked/created.")
            cursor.close()
            connection.close()
    except mysql.connector.Error as e:
        print(f"[MySQL Init Error] {e}")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base

# Update this with your actual PostgreSQL credentials
DB_URL = "postgresql://postgres:pgadmin4@localhost/khata_db"

engine = create_engine(DB_URL)
Session = sessionmaker(bind=engine)
session = Session()

Base.metadata.create_all(engine)
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv
import os

load_dotenv()

# Get DATABASE_URL from .env
DATABASE_URL = os.getenv("db_url")

# DATABASE_URL = "postgresql+psycopg2://postgres:55555@localhost:5432/test_db"
print('DB Connection: ',DATABASE_URL)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


# Join using core sqlAlchemy
# from sqlalchemy import select, join
# left = join(User, Order, User.id == Order.user_id, isouter=True)  
# stmt = select(User, Order).select_from(left)
# result = db.execute(stmt).all()

# queries and subqueries

# from sqlalchemy import select

# subq = select(orders.c.user_id).distinct().subquery()

# stmt = select(users).where(users.c.id.in_(select(subq.c.user_id)))
# result = db.execute(stmt).all()


# Associations many-to-many

# class UserCourse(Base):
#     __tablename__ = "user_course"

#     user_id = Column(ForeignKey("users.id"), primary_key=True)
#     course_id = Column(ForeignKey("courses.id"), primary_key=True)
#     enrollment_date = Column(String, nullable=False)
#     grade = Column(String)

#     user = relationship("User", back_populates="course_associations")
#     course = relationship("Course", back_populates="user_associations")

# class User(Base):
#     __tablename__ = "users"
#     id = Column(Integer, primary_key=True)
#     name = Column(String(50))

#     course_associations = relationship("UserCourse", back_populates="user")


# class Course(Base):
#     __tablename__ = "courses"
#     id = Column(Integer, primary_key=True)
#     title = Column(String(100))

#     user_associations = relationship("UserCourse", back_populates="course")
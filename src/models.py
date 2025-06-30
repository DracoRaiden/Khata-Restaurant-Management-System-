from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Numeric, Boolean, Text, ForeignKey, Date, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    user_id = Column(Integer, primary_key=True)
    name = Column(String(100))
    role = Column(String(50))
    contact = Column(String(100))
    email = Column(String(100), unique=True)
    password = Column(String(255))

    # Relationships
    orders = relationship("Order", back_populates="user", cascade="all, delete-orphan")
    feedbacks = relationship("Feedback", back_populates="user", cascade="all, delete-orphan")


class Order(Base):
    __tablename__ = 'orders'

    order_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.user_id'))
    table_id = Column(Integer, ForeignKey('tables.table_id'))
    status = Column(String(50), default="Pending")
    total_amount = Column(Numeric(10, 2))
    payment_status = Column(String(50), default="Unpaid")
    order_time = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="orders")
    order_items = relationship("OrderItems", back_populates="order", cascade="all, delete-orphan")
    feedbacks = relationship("Feedback", back_populates="order", cascade="all, delete-orphan")


class Feedback(Base):
    __tablename__ = 'feedback'

    feedback_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.user_id'))
    order_id = Column(Integer, ForeignKey('orders.order_id'))
    rating = Column(Integer)
    comments = Column(Text)

    # Relationships
    user = relationship("User", back_populates="feedbacks")
    order = relationship("Order", back_populates="feedbacks")


class Table(Base):
    __tablename__ = 'tables'
    table_id = Column(Integer, primary_key=True)
    capacity = Column(Integer)
    availability = Column(Boolean, default=True)

class Reservation(Base):
    __tablename__ = 'reservations'
    reservation_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.user_id'))
    table_id = Column(Integer, ForeignKey('tables.table_id'))
    reservation_time = Column(DateTime)
    status = Column(String(50), default="Confirmed")

class Payment(Base):
    __tablename__ = 'payments'
    payment_id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey('orders.order_id'))
    payment_type = Column(String(50))
    amount = Column(Numeric(10, 2))
    status = Column(String(50), default="Pending")

class Inventory(Base):
    __tablename__ = 'inventory'
    item_id = Column(Integer, primary_key=True)
    name = Column(String(100))
    quantity = Column(Integer)
    expiry_date = Column(Date)
    supplier_id = Column(Integer)


class MenuItem(Base):
    __tablename__ = 'menu_items'

    item_id = Column(Integer, primary_key=True)
    name = Column(String(100))
    category = Column(String(50))
    price = Column(Numeric(10, 2))
    availability = Column(Boolean, default=True)
    ingredients = Column(Text)

    # Relationship to OrderItems
    order_items = relationship("OrderItems", back_populates="menu_item", cascade="all, delete-orphan")


class OrderItems(Base):
    __tablename__ = 'OrderItems'

    order_item_id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey('orders.order_id'))
    item_id = Column(Integer, ForeignKey('menu_items.item_id'))
    quantity = Column(Integer)
    total_price = Column(Numeric(10, 2))  # Ensure this is here

    order = relationship("Order", back_populates="order_items")
    menu_item = relationship("MenuItem", back_populates="order_items")

class ArchivedOrder(Base):
    __tablename__ = 'archived_orders'

    order_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.user_id', ondelete='SET NULL'), nullable=True)
    table_id = Column(Integer, ForeignKey('tables.table_id', ondelete='SET NULL'), nullable=True)
    status = Column(String(50))
    total_amount = Column(Numeric(10, 2))
    payment_status = Column(String(50))
    order_time = Column(DateTime)
    archive_time = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", backref="archived_orders", foreign_keys=[user_id])
    table = relationship("Table", backref="archived_orders", foreign_keys=[table_id])

    def _repr_(self):
        return f"<ArchivedOrder(order_id={self.order_id}, user_id={self.user_id}, status={self.status})>"


class ArchivedOrderItems(Base):
    __tablename__ = 'archived_order_items'

    item_id = Column(Integer, primary_key=True)
    order_id = Column(Integer)
    menu_item_id = Column(Integer)
    quantity = Column(Integer)
    total_price = Column(Numeric(10, 2))

    def _repr_(self):
        return f"<ArchivedOrderItems(order_id={self.order_id}, menu_item_id={self.menu_item_id}, quantity={self.quantity})>"


# Adding back_populates to the Order model to establish the relationship
Order.order_items = relationship('OrderItems', back_populates='order')
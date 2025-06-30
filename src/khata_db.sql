-- USERS TABLE
CREATE TABLE Users (
    user_id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    role VARCHAR(50) CHECK (role IN ('Admin', 'Staff', 'Customer', 'Receptionist')) NOT NULL,
    contact VARCHAR(100),
    email VARCHAR(100) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL
);

-- MENU ITEMS
CREATE TABLE Menu_Items (
    item_id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    category VARCHAR(50) NOT NULL,
    price NUMERIC(10,2) NOT NULL,
    availability BOOLEAN DEFAULT TRUE,
    ingredients TEXT
);

-- ORDERS
CREATE TABLE Orders (
    order_id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES Users(user_id),
    table_id INTEGER,
    status VARCHAR(50) CHECK (status IN ('Pending', 'In Progress', 'Completed')) DEFAULT 'Pending',
    total_amount NUMERIC(10,2),
    payment_status VARCHAR(50) DEFAULT 'Unpaid',
    order_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


-- TABLES
CREATE TABLE Tables (
    table_id SERIAL PRIMARY KEY,
    capacity INTEGER NOT NULL,
    availability BOOLEAN DEFAULT TRUE
);

-- RESERVATIONS
CREATE TABLE Reservations (
    reservation_id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES Users(user_id),
    table_id INTEGER REFERENCES Tables(table_id),
    reservation_time TIMESTAMP NOT NULL,
    status VARCHAR(50) CHECK (status IN ('Confirmed', 'Cancelled', 'No-Show')) DEFAULT 'Confirmed'
);

-- PAYMENTS
CREATE TABLE Payments (
    payment_id SERIAL PRIMARY KEY,
    order_id INTEGER REFERENCES Orders(order_id),
    payment_type VARCHAR(50),
    amount NUMERIC(10,2),
    status VARCHAR(50) DEFAULT 'Pending'
);

-- INVENTORY
CREATE TABLE Inventory (
    item_id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    quantity INTEGER NOT NULL,
    expiry_date DATE,
    supplier_id INTEGER
);

-- FEEDBACK
CREATE TABLE Feedback (
    feedback_id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES Users(user_id),
    order_id INTEGER REFERENCES Orders(order_id),
    rating INTEGER CHECK (rating BETWEEN 1 AND 5),
    comments TEXT
);

-- ORDER ITEM TABLE
CREATE TABLE OrderItems (
    order_item_id SERIAL PRIMARY KEY,
    order_id INTEGER REFERENCES Orders(order_id) ON DELETE CASCADE,
    item_id INTEGER REFERENCES Menu_Items(item_id),
    quantity INTEGER NOT NULL,
    total_price NUMERIC(10,2) NOT NULL
);

ALTER TABLE order_items ADD COLUMN total_price NUMERIC(10, 2);

-- Admin
INSERT INTO users (name, role, contact, email, password)
VALUES ('Admin User', 'Admin', '03338255284', 'admin@khata.com', 'admin123');

-- Staff
INSERT INTO users (name, role, contact, email, password)
VALUES 
('Waiter A', 'Staff', '03000000000', 'waiter@khata.com', 'waiter123'),
('Chef A', 'Staff', '03000000001', 'chef@khata.com', 'chef123');

-- Receptionist
INSERT INTO users (name, role, contact, email, password)
VALUES ('Receptionist A', 'Receptionist', '03001112222', 'reception@khata.com', 'reception123');

-- Customer
INSERT INTO users (name, role, contact, email, password)
VALUES ('Customer A', 'Customer', '03007775555', 'customer@khata.com', 'customer123');


SELECT * FROM Users;
SELECT * FROM Menu_Items;

-- Drop existing foreign keys
ALTER TABLE Orders DROP CONSTRAINT IF EXISTS orders_user_id_fkey;
ALTER TABLE Feedback DROP CONSTRAINT IF EXISTS feedback_user_id_fkey;
ALTER TABLE Feedback DROP CONSTRAINT IF EXISTS feedback_order_id_fkey;

-- Add cascade delete on Orders → Users
ALTER TABLE Orders
ADD CONSTRAINT orders_user_id_fkey
FOREIGN KEY (user_id)
REFERENCES Users(user_id)
ON DELETE CASCADE;

-- Add cascade delete on Feedback → Users
ALTER TABLE Feedback
ADD CONSTRAINT feedback_user_id_fkey
FOREIGN KEY (user_id)
REFERENCES Users(user_id)
ON DELETE CASCADE;

-- Add cascade delete on Feedback → Orders
ALTER TABLE Feedback
ADD CONSTRAINT feedback_order_id_fkey
FOREIGN KEY (order_id)
REFERENCES Orders(order_id)
ON DELETE CASCADE;


-- Archived Orders Table
CREATE TABLE archived_orders (
    order_id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(user_id) ON DELETE SET NULL,  -- Ensuring that if the user is deleted, the order remains with null user_id
    table_id INTEGER,  -- This can be an integer, assuming you are keeping track of the table in the archive as well
    status VARCHAR(50),
    total_amount NUMERIC(10, 2),
    payment_status VARCHAR(50),
    order_time TIMESTAMP,
    archive_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_table_id FOREIGN KEY (table_id) REFERENCES tables(table_id) ON DELETE SET NULL  -- Ensures the reference to tables is handled even if the table is deleted
);


-- 1. Create the archived_orders table (if not already created)
CREATE TABLE IF NOT EXISTS archived_orders (
    order_id INTEGER PRIMARY KEY,
    user_id INTEGER,
    table_id INTEGER,
    status VARCHAR(50),
    total_amount NUMERIC(10,2),
    payment_status VARCHAR(50),
    order_time TIMESTAMP,
    archive_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Create the trigger function
CREATE OR REPLACE FUNCTION archive_order_before_delete()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO archived_orders (
        order_id, user_id, table_id, status,
        total_amount, payment_status, order_time
    )
    VALUES (
        OLD.order_id, OLD.user_id, OLD.table_id, OLD.status,
        OLD.total_amount, OLD.payment_status, OLD.order_time
    );

    RETURN OLD;
END;
$$ LANGUAGE plpgsql;

-- 3. Attach the trigger to the Orders table
CREATE TRIGGER trigger_archive_order
BEFORE DELETE ON orders
FOR EACH ROW
EXECUTE FUNCTION archive_order_before_delete();


CREATE TABLE archived_order_items (
    item_id SERIAL PRIMARY KEY,
    order_id INTEGER,
    menu_item_id INTEGER,
    quantity INTEGER,
    total_price NUMERIC(10,2)
);

CREATE OR REPLACE FUNCTION archive_order_and_items_before_delete()
RETURNS TRIGGER AS $$
BEGIN
    -- Archive the order
    INSERT INTO archived_orders (
        order_id, user_id, table_id, status,
        total_amount, payment_status, order_time
    )
    VALUES (
        OLD.order_id, OLD.user_id, OLD.table_id, OLD.status,
        OLD.total_amount, OLD.payment_status, OLD.order_time
    );

    -- Archive related order items
    INSERT INTO archived_order_items (order_id, menu_item_id, quantity, total_price)
    SELECT 
        oi.order_id,
        oi.menu_item_id,
        oi.quantity,
        oi.total_price
    FROM order_items oi
    WHERE oi.order_id = OLD.order_id;

    RETURN OLD;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_archive_order ON orders;

CREATE TRIGGER trigger_archive_order
BEFORE DELETE ON orders
FOR EACH ROW
EXECUTE FUNCTION archive_order_and_items_before_delete();


ALTER TABLE order_items
DROP CONSTRAINT order_items_order_id_fkey,
ADD CONSTRAINT order_items_order_id_fkey
FOREIGN KEY (order_id) REFERENCES orders(order_id)
ON DELETE CASCADE;

ALTER TABLE orders
    DROP CONSTRAINT orders_status_check;
    
ALTER TABLE orders
    ADD CONSTRAINT orders_status_check
    CHECK (status IN ('Pending', 'In Progress', 'Completed', 'Archived'));


CREATE OR REPLACE FUNCTION archive_order_and_items_before_delete() 
RETURNS TRIGGER AS $$
BEGIN
    -- Insert the order into the archived_orders table, allowing for NULL table_id
    INSERT INTO archived_orders (order_id, user_id, table_id, status, total_amount, payment_status, order_time, archive_time)
    VALUES (
        OLD.order_id,
        OLD.user_id,
        -- If the table_id doesn't exist in the tables table, set it to NULL
        COALESCE(OLD.table_id, NULL),
        OLD.status,
        OLD.total_amount,
        OLD.payment_status,
        OLD.order_time,
        CURRENT_TIMESTAMP
    );

    -- Insert order items into the archived_order_items table
    INSERT INTO archived_order_items (order_id, menu_item_id, quantity, total_price)
    SELECT OLD.order_id, menu_item_id, quantity, total_price
    FROM order_items
    WHERE order_id = OLD.order_id;

    -- Return NULL to indicate that the delete should proceed
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

ALTER TABLE archived_orders
    DROP CONSTRAINT fk_table_id,
    ADD CONSTRAINT fk_table_id FOREIGN KEY (table_id) REFERENCES tables(table_id) ON DELETE SET NULL;


CREATE OR REPLACE FUNCTION archive_order_and_items_before_delete() 
RETURNS TRIGGER AS $$
BEGIN
    -- Check if the table_id exists in the tables table
    IF NOT EXISTS (SELECT 1 FROM tables WHERE table_id = OLD.table_id) THEN
        -- If table_id does not exist, set it to NULL or some default value
        INSERT INTO archived_orders (order_id, user_id, table_id, status, total_amount, payment_status, order_time, archive_time)
        VALUES (
            OLD.order_id,
            OLD.user_id,
            NULL, -- Set table_id to NULL if it doesn't exist in the tables table
            OLD.status,
            OLD.total_amount,
            OLD.payment_status,
            OLD.order_time,
            CURRENT_TIMESTAMP
        );
    ELSE
        -- If table_id exists, proceed as normal
        INSERT INTO archived_orders (order_id, user_id, table_id, status, total_amount, payment_status, order_time, archive_time)
        VALUES (
            OLD.order_id,
            OLD.user_id,
            OLD.table_id, -- Keep the original table_id
            OLD.status,
            OLD.total_amount,
            OLD.payment_status,
            OLD.order_time,
            CURRENT_TIMESTAMP
        );
    END IF;

    -- Archive the order items
    INSERT INTO archived_order_items (order_id, menu_item_id, quantity, total_price)
    SELECT OLD.order_id, menu_item_id, quantity, total_price
    FROM order_items
    WHERE order_id = OLD.order_id;

    -- Return NULL to proceed with the delete
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;


DROP TRIGGER IF EXISTS archive_order_trigger ON orders;


CREATE TRIGGER archive_order_trigger
AFTER DELETE ON orders
FOR EACH ROW
EXECUTE FUNCTION archive_order_and_items_before_delete();



CREATE OR REPLACE FUNCTION archive_order_and_items_before_delete() 
RETURNS TRIGGER AS $$
BEGIN
    -- Prevent duplicate archiving
    IF EXISTS (SELECT 1 FROM archived_orders WHERE order_id = OLD.order_id) THEN
        RETURN OLD; -- Already archived, skip to avoid UNIQUE violation
    END IF;

    -- Archive the order details
    INSERT INTO archived_orders (
        order_id, user_id, table_id, status, total_amount, payment_status, order_time, archive_time
    )
    VALUES (
        OLD.order_id,
        OLD.user_id,
        (SELECT table_id FROM tables WHERE table_id = OLD.table_id),
        OLD.status,
        OLD.total_amount,
        OLD.payment_status,
        OLD.order_time,
        CURRENT_TIMESTAMP
    );

    -- Archive the order items
    INSERT INTO archived_order_items (order_id, menu_item_id, quantity, total_price)
    SELECT 
        OLD.order_id, 
        oi.item_id, 
        oi.quantity, 
        oi.total_price
    FROM OrderItems oi
    WHERE oi.order_id = OLD.order_id;

    RETURN OLD;  -- Proceed with the deletion
END;
$$ LANGUAGE plpgsql;


-- Drop the old trigger if it exists
DROP TRIGGER IF EXISTS archive_order_trigger ON orders;

-- Create BEFORE DELETE trigger
CREATE TRIGGER archive_order_trigger
BEFORE DELETE ON orders
FOR EACH ROW
EXECUTE FUNCTION archive_order_and_items_before_delete();

SELECT * FROM OrderItems;
SELECT * FROM Users;

SELECT * FROM order_items;

-- 2) The BEFORE DELETE trigger on "orders" now archives both order and its items:
CREATE OR REPLACE FUNCTION archive_order_and_items_before_delete()
  RETURNS TRIGGER AS $$
BEGIN
  -- Skip if already archived
  IF EXISTS (SELECT 1 FROM archived_orders WHERE order_id = OLD.order_id) THEN
    RETURN OLD;
  END IF;

  -- Archive the order itself
  INSERT INTO archived_orders (
    order_id, user_id, table_id, status,
    total_amount, payment_status, order_time, archive_time
  )
  VALUES (
    OLD.order_id,
    OLD.user_id,
    OLD.table_id,
    OLD.status,
    OLD.total_amount,
    OLD.payment_status,
    OLD.order_time,
    CURRENT_TIMESTAMP
  );

  -- Archive each line‐item from order_items
  INSERT INTO archived_order_items (
    order_id, menu_item_id, quantity, total_price
  )
  SELECT
    oi.order_id,
    oi.item_id,
    oi.quantity,
    oi.total_price
  FROM order_items AS oi
  WHERE oi.order_id = OLD.order_id;

  RETURN OLD;  -- allow the DELETE to proceed
END;
$$ LANGUAGE plpgsql;

-- 3) Drop any old trigger and re-create it as BEFORE DELETE:
DROP TRIGGER IF EXISTS archive_order_trigger ON orders;

CREATE TRIGGER archive_order_trigger
  BEFORE DELETE ON orders
  FOR EACH ROW
  EXECUTE FUNCTION archive_order_and_items_before_delete();


-- 1. Drop the old FK
ALTER TABLE archived_orders
  DROP CONSTRAINT IF EXISTS fk_table_id;

-- 2. Allow NULLs in that column
ALTER TABLE archived_orders
  ALTER COLUMN table_id DROP NOT NULL;

-- 3. Re-add the FK with ON DELETE SET NULL
ALTER TABLE archived_orders
  ADD CONSTRAINT fk_table_id
    FOREIGN KEY(table_id)
    REFERENCES tables(table_id)
    ON DELETE SET NULL;



CREATE OR REPLACE FUNCTION archive_order_and_items_before_delete() 
RETURNS TRIGGER AS $$
BEGIN
    -- Prevent duplicate archiving
    IF EXISTS (SELECT 1 FROM archived_orders WHERE order_id = OLD.order_id) THEN
        RETURN OLD; -- Already archived, skip to avoid UNIQUE violation
    END IF;

    -- Archive the order details, nulling out any missing table_id
    INSERT INTO archived_orders (
        order_id, user_id, table_id, status,
        total_amount, payment_status, order_time, archive_time
    )
    VALUES (
        OLD.order_id,
        OLD.user_id,
        CASE
          WHEN EXISTS (SELECT 1 FROM tables WHERE table_id = OLD.table_id)
            THEN OLD.table_id
          ELSE NULL
        END,
        OLD.status,
        OLD.total_amount,
        OLD.payment_status,
        OLD.order_time,
        CURRENT_TIMESTAMP
    );

    -- Archive the order items
    INSERT INTO archived_order_items (order_id, menu_item_id, quantity, total_price)
    SELECT
        OLD.order_id,
        oi.item_id,
        oi.quantity,
        oi.total_price
    FROM OrderItems oi
    WHERE oi.order_id = OLD.order_id;

    RETURN OLD;  -- Proceed with the deletion
END;
$$ LANGUAGE plpgsql;

-- Recreate the trigger
DROP TRIGGER IF EXISTS archive_order_trigger ON orders;

CREATE TRIGGER archive_order_trigger
BEFORE DELETE ON orders
FOR EACH ROW
EXECUTE FUNCTION archive_order_and_items_before_delete();


INSERT INTO tables (capacity, availability) VALUES
  (2, TRUE),
  (4, TRUE),
  (6, TRUE);

-- Disable foreign key checks temporarily to allow dropping tables in any order
SET FOREIGN_KEY_CHECKS = 0;

-- 1. Create the database if it doesn't exist
--    (You might need to execute this part with a user that has CREATE DATABASE privileges,
--     e.g., 'root', and without specifying a database initially, then use `USE car_rental_db;`)
CREATE DATABASE IF NOT EXISTS car_rental_db;

-- 2. Switch to the newly created or existing database
USE car_rental_db;

-- 3. Drop tables in reverse dependency order to ensure clean slate (if they exist)
DROP TABLE IF EXISTS payment;
DROP TABLE IF EXISTS rental;
DROP TABLE IF EXISTS car;
DROP TABLE IF EXISTS customer;
DROP TABLE IF EXISTS staff;

-- 4. Create Tables

-- Table: staff
CREATE TABLE staff (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    first_name VARCHAR(255) NOT NULL,
    last_name VARCHAR(255) NOT NULL,
    -- Using ENUM to restrict roles to specific values
    role ENUM('Agent', 'Manager', 'Administrator') NOT NULL DEFAULT 'Agent'
) ENGINE=InnoDB;

-- Table: customer
CREATE TABLE customer (
    id INT AUTO_INCREMENT PRIMARY KEY,
    first_name VARCHAR(255) NOT NULL,
    last_name VARCHAR(255) NOT NULL,
    phone VARCHAR(20),
    email VARCHAR(255) UNIQUE NOT NULL
) ENGINE=InnoDB;

-- Table: car
CREATE TABLE car (
    id INT AUTO_INCREMENT PRIMARY KEY,
    reg_number VARCHAR(50) UNIQUE NOT NULL,
    brand VARCHAR(100) NOT NULL,
    model VARCHAR(100) NOT NULL,
    year INT NOT NULL,
    rate DECIMAL(10, 2) NOT NULL,
    -- Status can be 'A' (Available), 'R' (Rented), 'M' (Maintenance)
    status ENUM('A', 'R', 'M') NOT NULL DEFAULT 'A'
) ENGINE=InnoDB;

-- Table: rental
CREATE TABLE rental (
    id INT AUTO_INCREMENT PRIMARY KEY,
    customer_id INT NOT NULL,
    car_id INT NOT NULL,
    rent_date DATE NOT NULL,
    expected_return_date DATE NOT NULL,
    actual_return_date DATE,
    FOREIGN KEY (customer_id) REFERENCES customer(id) ON DELETE CASCADE,
    FOREIGN KEY (car_id) REFERENCES car(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- Table: payment
CREATE TABLE payment (
    id INT AUTO_INCREMENT PRIMARY KEY,
    rental_id INT NOT NULL,
    amount DECIMAL(10, 2) NOT NULL,
    payment_date DATE NOT NULL,
    FOREIGN KEY (rental_id) REFERENCES rental(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- 5. Insert Initial Data
-- Insert an administrator staff member
INSERT INTO staff (username, email, first_name, last_name, role)
VALUES ('admin', 'admin@example.com', 'System', 'Admin', 'Administrator');

-- Enable foreign key checks again
SET FOREIGN_KEY_CHECKS = 1;

-- Confirmation Message (optional, for script execution)
SELECT 'Database schema and initial data setup complete!' AS Message;
-- Create the database if it doesn't already exist
CREATE DATABASE IF NOT EXISTS `grillgrade_db`;

-- Select the database to use for the following commands
USE `grillgrade_db`;

-- Creates the "parent" table that holds information about each restaurant table.
CREATE TABLE IF NOT EXISTS `restaurant_table` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `capacity` INT NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB;

-- Creates the "child" table to store all customer bookings.
CREATE TABLE IF NOT EXISTS `booking` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `table_id` INT NOT NULL,
  `customer_name` VARCHAR(255) NOT NULL,
  `guests` INT NOT NULL,
  `booking_date` DATE NOT NULL,
  `booking_time` TIME NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uc_booking` (`table_id`, `booking_date`, `booking_time`),
  FOREIGN KEY (`table_id`) REFERENCES `restaurant_table`(`id`)
) ENGINE=InnoDB;


-- FINAL FIX: Temporarily disable Safe Update Mode to allow DELETE without a WHERE clause.
SET SQL_SAFE_UPDATES = 0;

-- Empty the tables in the correct order (child first, then parent).
DELETE FROM `booking`;
DELETE FROM `restaurant_table`;

-- Re-enable Safe Update Mode for safety.
SET SQL_SAFE_UPDATES = 1;


-- Inserts a new table layout with a total capacity of 20 seats
INSERT INTO `restaurant_table` (capacity) VALUES
(4), -- Table 1 has 4 seats
(4), -- Table 2 has 4 seats
(6), -- Table 3 has 6 seats
(2), -- Table 4 has 2 seats
(4); -- Table 5 has 4 seats
-- Total Seats = 4 + 4 + 6 + 2 + 4 = 20
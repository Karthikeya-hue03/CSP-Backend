-- =====================================================================
-- AI-Powered Campus Infrastructure Health Monitoring & Predictive Maintenance System
-- Database Schema and Demo Data Script for MySQL
-- =====================================================================

CREATE DATABASE IF NOT EXISTS campus_maintenance;
USE campus_maintenance;

-- Drop tables in reverse order of foreign key dependencies
DROP TABLE IF EXISTS ai_predictions;
DROP TABLE IF EXISTS survey_responses;
DROP TABLE IF EXISTS surveys;
DROP TABLE IF EXISTS alerts;
DROP TABLE IF EXISTS maintenance;
DROP TABLE IF EXISTS drainage;
DROP TABLE IF EXISTS water_pipelines;
DROP TABLE IF EXISTS roads;
DROP TABLE IF EXISTS streetlights;
DROP TABLE IF EXISTS assets;
DROP TABLE IF EXISTS users;

-- ---------------------------------------------------------------------
-- 1. USERS TABLE
-- ---------------------------------------------------------------------
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('Admin', 'Maintenance Staff', 'Viewer') NOT NULL DEFAULT 'Viewer',
    phone VARCHAR(20),
    department VARCHAR(100) DEFAULT 'Campus Estate Office',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ---------------------------------------------------------------------
-- 2. ASSETS (MASTER TABLE)
-- ---------------------------------------------------------------------
CREATE TABLE assets (
    id INT AUTO_INCREMENT PRIMARY KEY,
    asset_tag VARCHAR(50) UNIQUE NOT NULL,
    asset_type ENUM('streetlight', 'road', 'water_pipeline', 'drainage') NOT NULL,
    name VARCHAR(150) NOT NULL,
    location VARCHAR(200) NOT NULL,
    latitude DECIMAL(10, 7) NOT NULL,
    longitude DECIMAL(10, 7) NOT NULL,
    health_score INT NOT NULL DEFAULT 100,
    condition_status ENUM('Good', 'Moderate', 'Poor', 'Critical') NOT NULL DEFAULT 'Good',
    age_years INT NOT NULL DEFAULT 1,
    previous_failures INT NOT NULL DEFAULT 0,
    complaint_count INT NOT NULL DEFAULT 0,
    maintenance_count INT NOT NULL DEFAULT 0,
    last_inspection DATE,
    next_maintenance DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ---------------------------------------------------------------------
-- 3. STREETLIGHTS TABLE
-- ---------------------------------------------------------------------
CREATE TABLE streetlights (
    id INT AUTO_INCREMENT PRIMARY KEY,
    asset_id INT NOT NULL UNIQUE,
    pole_number VARCHAR(50) NOT NULL,
    wattage INT DEFAULT 70,
    power_status ENUM('ON', 'OFF') DEFAULT 'ON',
    light_status ENUM('Working', 'Flickering', 'Faulty', 'Power Off', 'Maintenance Required') DEFAULT 'Working',
    lumens INT DEFAULT 6500,
    FOREIGN KEY (asset_id) REFERENCES assets(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ---------------------------------------------------------------------
-- 4. ROADS TABLE
-- ---------------------------------------------------------------------
CREATE TABLE roads (
    id INT AUTO_INCREMENT PRIMARY KEY,
    asset_id INT NOT NULL UNIQUE,
    road_name VARCHAR(150) NOT NULL,
    length_km DECIMAL(6, 2) DEFAULT 1.0,
    surface_type VARCHAR(50) DEFAULT 'Asphalt',
    pothole_count INT DEFAULT 0,
    crack_severity ENUM('None', 'Minor', 'Moderate', 'Severe') DEFAULT 'None',
    road_condition ENUM('Good', 'Moderate', 'Poor', 'Critical') DEFAULT 'Good',
    priority ENUM('Low', 'Medium', 'High', 'Urgent') DEFAULT 'Medium',
    FOREIGN KEY (asset_id) REFERENCES assets(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ---------------------------------------------------------------------
-- 5. WATER PIPELINES TABLE
-- ---------------------------------------------------------------------
CREATE TABLE water_pipelines (
    id INT AUTO_INCREMENT PRIMARY KEY,
    asset_id INT NOT NULL UNIQUE,
    pipeline_code VARCHAR(50) NOT NULL,
    length_km DECIMAL(6, 2) DEFAULT 0.5,
    pipe_material VARCHAR(50) DEFAULT 'HDPE',
    leak_status ENUM('Normal', 'Leak Detected', 'Low Flow', 'Critical') DEFAULT 'Normal',
    water_flow_rate DECIMAL(6, 2) DEFAULT 45.0,
    pressure_psi DECIMAL(6, 2) DEFAULT 55.0,
    FOREIGN KEY (asset_id) REFERENCES assets(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ---------------------------------------------------------------------
-- 6. DRAINAGE TABLE
-- ---------------------------------------------------------------------
CREATE TABLE drainage (
    id INT AUTO_INCREMENT PRIMARY KEY,
    asset_id INT NOT NULL UNIQUE,
    drain_code VARCHAR(50) NOT NULL,
    drain_type VARCHAR(50) DEFAULT 'Storm Water',
    flow_status ENUM('Normal', 'Blocked', 'Overflow', 'Critical') DEFAULT 'Normal',
    blockage_level ENUM('None', 'Partial', 'Severe', 'Total') DEFAULT 'None',
    stagnation_risk ENUM('Low', 'Moderate', 'High') DEFAULT 'Low',
    FOREIGN KEY (asset_id) REFERENCES assets(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ---------------------------------------------------------------------
-- 7. MAINTENANCE WORK ORDERS
-- ---------------------------------------------------------------------
CREATE TABLE maintenance (
    id INT AUTO_INCREMENT PRIMARY KEY,
    maintenance_code VARCHAR(50) UNIQUE NOT NULL,
    asset_id INT NOT NULL,
    problem TEXT NOT NULL,
    priority ENUM('Low', 'Medium', 'High', 'Urgent') DEFAULT 'Medium',
    assigned_staff_id INT,
    created_date DATE NOT NULL,
    due_date DATE,
    status ENUM('Pending', 'Assigned', 'In Progress', 'Completed') DEFAULT 'Pending',
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (asset_id) REFERENCES assets(id) ON DELETE CASCADE,
    FOREIGN KEY (assigned_staff_id) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ---------------------------------------------------------------------
-- 8. PREDICTIVE ALERTS
-- ---------------------------------------------------------------------
CREATE TABLE alerts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    asset_id INT NOT NULL,
    alert_type ENUM('Critical', 'Warning', 'Maintenance') NOT NULL,
    problem VARCHAR(255) NOT NULL,
    risk_level ENUM('High Risk', 'Medium Risk', 'Low Risk') NOT NULL,
    recommended_action TEXT NOT NULL,
    status ENUM('Pending', 'In Progress', 'Resolved') DEFAULT 'Pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (asset_id) REFERENCES assets(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ---------------------------------------------------------------------
-- 9. CAMPUS SURVEYS & RESPONSES
-- ---------------------------------------------------------------------
CREATE TABLE surveys (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE survey_responses (
    id INT AUTO_INCREMENT PRIMARY KEY,
    survey_id INT DEFAULT 1,
    respondent_name VARCHAR(100),
    respondent_role ENUM('Student', 'Faculty', 'Staff', 'Visitor') DEFAULT 'Student',
    streetlights_working ENUM('Yes', 'Mostly', 'No') DEFAULT 'Yes',
    streetlights_flickering ENUM('None', 'A Few', 'Many') DEFAULT 'None',
    roads_potholes ENUM('None', 'Minor', 'Severe') DEFAULT 'None',
    roads_maintenance_needed ENUM('Yes', 'No', 'Unsure') DEFAULT 'No',
    water_leakage_observed ENUM('None', 'Occasional', 'Frequent') DEFAULT 'None',
    water_supply_regular ENUM('Yes', 'Usually', 'No') DEFAULT 'Yes',
    drainage_blocked ENUM('None', 'Sometimes', 'Frequently') DEFAULT 'None',
    drainage_flow_ok ENUM('Good', 'Slow', 'Overflowing') DEFAULT 'Good',
    maintenance_satisfaction INT DEFAULT 4,
    maintenance_timely ENUM('Always', 'Usually', 'Rarely', 'Never') DEFAULT 'Usually',
    ai_monitoring_useful ENUM('Extremely', 'Very', 'Somewhat', 'Not Useful') DEFAULT 'Extremely',
    ai_would_use ENUM('Definitely', 'Probably', 'Unsure') DEFAULT 'Definitely',
    comments TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (survey_id) REFERENCES surveys(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ---------------------------------------------------------------------
-- 10. AI PREDICTIONS LOG
-- ---------------------------------------------------------------------
CREATE TABLE ai_predictions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    asset_id INT NOT NULL,
    health_score INT NOT NULL,
    failure_probability DECIMAL(5, 2) NOT NULL,
    risk_level ENUM('Low Risk', 'Medium Risk', 'High Risk') NOT NULL,
    predicted_failure_days INT NOT NULL,
    recommended_window VARCHAR(100) NOT NULL,
    features_json TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (asset_id) REFERENCES assets(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- =====================================================================
-- SEED DEMO DATA
-- =====================================================================

-- Users (Admin, Staff, Viewer)
-- Passwords are: Admin@123, Staff@123, Viewer@123
INSERT INTO users (id, name, email, password_hash, role, phone, department) VALUES
(1, 'Dr. Rajesh Kumar (Estate Director)', 'admin@campus.edu', 'scrypt:32768:8:1$akQ8e2JjwUYqvC8W$32457d47a85d6b61aaa81fd001f9113ad40c0366fb904375df332787cec528c2cf45a867a164cabe4c88d79fb49fcf6c599054e70742bb6233a0e4bbce82ce23', 'Admin', '+91 98480 12345', 'Infrastructure & Maintenance Office'),
(2, 'Venkatesh Rao (Lead Field Engineer)', 'staff@campus.edu', 'scrypt:32768:8:1$YLj6D6ttF2aoA7DB$c93e90b99e5ca6e9ef5a4acf70c889414b96e31da763d1ff359e5c289c16a9bafbb4a4e761a28dd0765b85687bfa20df2ae0d9ab567844c737b249d723e2ae66', 'Maintenance Staff', '+91 98480 56789', 'Campus Physical Plant Team'),
(3, 'Prof. Sunita Sharma (Campus Observer)', 'viewer@campus.edu', 'scrypt:32768:8:1$t1juxbBS4vG4WVyx$ae4457ba19bdd418cd3b12ab81147ddd6bbb2f68b3920fd527b03d7ec0064ea470440443a0589685f85ceb1988b086a722c1c280329ab9bd904f32e0583747f7', 'Viewer', '+91 98480 99887', 'Academic Council Representative');

-- Default Survey Record
INSERT INTO surveys (id, title, description, is_active) VALUES
(1, 'Campus Infrastructure Health & AI Survey 2026', 'Annual evaluation of roads, streetlights, water supply, drainage and AI preventive monitoring feedback from students and faculty.', TRUE);

-- Master Assets: Streetlights (22 assets: id 1 to 22, SRGEC Campus Coordinates: ~16.350975, 81.042576)
INSERT INTO assets (id, asset_tag, asset_type, name, location, latitude, longitude, health_score, condition_status, age_years, previous_failures, complaint_count, maintenance_count, last_inspection, next_maintenance) VALUES
(1, 'SL-001', 'streetlight', 'LED Pole 01 - Main Gate Entrance', 'Main Campus Gate', 16.350794, 81.042508, 95, 'Good', 1, 0, 0, 0, '2026-09-01', '2026-12-01'),
(2, 'SL-002', 'streetlight', 'LED Pole 02 - Admin Block Avenue', 'Administrative Block Avenue', 16.351054, 81.042738, 92, 'Good', 2, 0, 1, 1, '2026-08-25', '2026-11-25'),
(3, 'SL-003', 'streetlight', 'LED Pole 03 - Central Library North', 'Library North Walkway', 16.351354, 81.042238, 88, 'Good', 2, 1, 0, 1, '2026-08-10', '2026-11-10'),
(4, 'SL-004', 'streetlight', 'LED Pole 04 - Engineering Block B', 'Computer Science Quad', 16.351554, 81.042938, 78, 'Moderate', 3, 2, 2, 2, '2026-07-15', '2026-10-15'),
(5, 'SL-005', 'streetlight', 'LED Pole 05 - Boys Hostel Road', 'Hostel Zone Circle', 16.351954, 81.042038, 42, 'Poor', 5, 4, 5, 3, '2026-06-20', '2026-09-27'),
(6, 'SL-006', 'streetlight', 'LED Pole 06 - Sports Ground West', 'Cricket Pavilion Walkway', 16.350254, 81.041638, 31, 'Critical', 6, 6, 7, 4, '2026-06-11', '2026-09-22'),
(7, 'SL-007', 'streetlight', 'LED Pole 07 - Cafeteria Plaza', 'Central Food Court', 16.350654, 81.043338, 96, 'Good', 1, 0, 0, 0, '2026-09-05', '2026-12-05'),
(8, 'SL-008', 'streetlight', 'LED Pole 08 - Girls Hostel Avenue', 'East Hostel Lane', 16.352254, 81.043138, 68, 'Moderate', 3, 1, 3, 2, '2026-08-01', '2026-10-01'),
(9, 'SL-009', 'streetlight', 'LED Pole 09 - Science Lab Complex', 'Biotech Building Front', 16.350854, 81.041838, 84, 'Good', 2, 0, 1, 1, '2026-08-18', '2026-11-18'),
(10, 'SL-010', 'streetlight', 'LED Pole 10 - Mechanical Workshop', 'Workshop Perimeter', 16.349954, 81.042338, 52, 'Poor', 4, 3, 4, 3, '2026-07-22', '2026-10-05'),
(11, 'SL-011', 'streetlight', 'LED Pole 11 - Auditorium Boulevard', 'Convocation Hall Front', 16.350454, 81.042838, 90, 'Good', 1, 0, 0, 0, '2026-09-12', '2026-12-12'),
(12, 'SL-012', 'streetlight', 'LED Pole 12 - South Gate Checkpoint', 'South Campus Exit', 16.349554, 81.043038, 38, 'Critical', 5, 5, 6, 4, '2026-05-30', '2026-09-25'),
(13, 'SL-013', 'streetlight', 'LED Pole 13 - Innovation & Research Park', 'Tech Incubator Garden', 16.351654, 81.043638, 94, 'Good', 1, 0, 0, 0, '2026-09-08', '2026-12-08'),
(14, 'SL-014', 'streetlight', 'LED Pole 14 - Medical Center Junction', 'Health Center Crossing', 16.351854, 81.042638, 74, 'Moderate', 2, 1, 2, 1, '2026-08-14', '2026-11-14'),
(15, 'SL-015', 'streetlight', 'LED Pole 15 - Guest House Lane', 'VIP Guest Quarters', 16.351154, 81.041338, 91, 'Good', 1, 0, 0, 0, '2026-08-28', '2026-11-28'),
(16, 'SL-016', 'streetlight', 'LED Pole 16 - Indoor Stadium Court', 'Basketball Court North', 16.350154, 81.041038, 62, 'Moderate', 3, 2, 3, 2, '2026-07-19', '2026-10-19'),
(17, 'SL-017', 'streetlight', 'LED Pole 17 - Staff Quarters Block 1', 'Faculty Housing Sector A', 16.352454, 81.041838, 82, 'Good', 2, 1, 1, 1, '2026-08-22', '2026-11-22'),
(18, 'SL-018', 'streetlight', 'LED Pole 18 - Staff Quarters Block 2', 'Faculty Housing Sector B', 16.352654, 81.042138, 48, 'Poor', 4, 3, 4, 2, '2026-06-25', '2026-09-30'),
(19, 'SL-019', 'streetlight', 'LED Pole 19 - Parking Bay East', 'Central Vehicle Parking', 16.350554, 81.042038, 89, 'Good', 2, 0, 1, 1, '2026-09-02', '2026-12-02'),
(20, 'SL-020', 'streetlight', 'LED Pole 20 - Electrical Substation', 'Primary Power Yard', 16.349754, 81.042638, 35, 'Critical', 5, 4, 6, 3, '2026-05-18', '2026-09-23'),
(21, 'SL-021', 'streetlight', 'LED Pole 21 - Solar Farm Perimeter', 'Renewable Energy Wing', 16.349254, 81.041838, 87, 'Good', 2, 1, 0, 1, '2026-08-16', '2026-11-16'),
(22, 'SL-022', 'streetlight', 'LED Pole 22 - Lakeside Promenade', 'Campus Lake South Bank', 16.351254, 81.044038, 76, 'Moderate', 3, 2, 2, 2, '2026-07-29', '2026-10-29');

-- Streetlight Subtable
INSERT INTO streetlights (asset_id, pole_number, wattage, power_status, light_status, lumens) VALUES
(1, 'POL-01', 70, 'ON', 'Working', 7000),
(2, 'POL-02', 70, 'ON', 'Working', 6800),
(3, 'POL-03', 70, 'ON', 'Working', 6500),
(4, 'POL-04', 90, 'ON', 'Flickering', 5200),
(5, 'POL-05', 90, 'ON', 'Faulty', 2800),
(6, 'POL-06', 70, 'OFF', 'Power Off', 0),
(7, 'POL-07', 70, 'ON', 'Working', 7200),
(8, 'POL-08', 70, 'ON', 'Flickering', 5100),
(9, 'POL-09', 70, 'ON', 'Working', 6700),
(10, 'POL-10', 90, 'ON', 'Maintenance Required', 3400),
(11, 'POL-11', 70, 'ON', 'Working', 7100),
(12, 'POL-12', 90, 'OFF', 'Faulty', 0),
(13, 'POL-13', 70, 'ON', 'Working', 7000),
(14, 'POL-14', 70, 'ON', 'Working', 6100),
(15, 'POL-15', 70, 'ON', 'Working', 6900),
(16, 'POL-16', 90, 'ON', 'Flickering', 4600),
(17, 'POL-17', 70, 'ON', 'Working', 6400),
(18, 'POL-18', 70, 'ON', 'Maintenance Required', 3300),
(19, 'POL-19', 70, 'ON', 'Working', 6800),
(20, 'POL-20', 120, 'OFF', 'Power Off', 0),
(21, 'POL-21', 70, 'ON', 'Working', 6600),
(22, 'POL-22', 70, 'ON', 'Working', 6000);

-- Master Assets: Roads (12 assets: id 23 to 34)
INSERT INTO assets (id, asset_tag, asset_type, name, location, latitude, longitude, health_score, condition_status, age_years, previous_failures, complaint_count, maintenance_count, last_inspection, next_maintenance) VALUES
(23, 'RD-001', 'road', 'Main Entrance Boulevard', 'Main Gate to Admin Quad', 16.350904, 81.042588, 94, 'Good', 1, 0, 0, 1, '2026-09-02', '2026-12-02'),
(24, 'RD-002', 'road', 'University Central Spine Road', 'Admin to Library Connector', 16.351204, 81.042488, 86, 'Good', 2, 1, 1, 1, '2026-08-20', '2026-11-20'),
(25, 'RD-003', 'road', 'Engineering Ring Road East', 'Behind CS and IT Blocks', 16.351504, 81.043188, 72, 'Moderate', 3, 2, 3, 2, '2026-07-18', '2026-10-18'),
(26, 'RD-004', 'road', 'Hostel Transit Lane', 'North Student Residential Sector', 16.352104, 81.042438, 39, 'Critical', 5, 5, 7, 3, '2026-06-15', '2026-09-24'),
(27, 'RD-005', 'road', 'Sports Complex Access Way', 'Stadium Outer Ring', 16.350404, 81.041338, 78, 'Moderate', 2, 1, 1, 1, '2026-08-05', '2026-11-05'),
(28, 'RD-006', 'road', 'Workshop Heavy Haul Track', 'Behind Mechanical Fabrication Lab', 16.349854, 81.042138, 48, 'Poor', 4, 3, 5, 2, '2026-06-29', '2026-09-29'),
(29, 'RD-007', 'road', 'Cafeteria Pedestrian Way', 'Central Food Plaza Circle', 16.350704, 81.043138, 92, 'Good', 1, 0, 0, 1, '2026-09-10', '2026-12-10'),
(30, 'RD-008', 'road', 'Research Park Link Road', 'Biotech to Nanotech Facility', 16.351604, 81.043888, 89, 'Good', 2, 0, 1, 1, '2026-08-26', '2026-11-26'),
(31, 'RD-009', 'road', 'South Gate Freight Corridor', 'Logistics Terminal to Store', 16.349504, 81.042788, 34, 'Critical', 6, 6, 8, 4, '2026-05-22', '2026-09-21'),
(32, 'RD-010', 'road', 'Faculty Housing Internal Lane', 'Sector A Staff Enclave', 16.352604, 81.041988, 81, 'Good', 2, 1, 1, 1, '2026-08-12', '2026-11-12'),
(33, 'RD-011', 'road', 'Lake View Circular Drive', 'Waterfront Jogging & Service Path', 16.351404, 81.044288, 65, 'Moderate', 3, 2, 3, 2, '2026-07-25', '2026-10-25'),
(34, 'RD-012', 'road', 'Auditorium North Crescent', 'Behind Convocation Lawn', 16.350354, 81.043088, 88, 'Good', 2, 0, 0, 0, '2026-09-04', '2026-12-04');

-- Road Subtable
INSERT INTO roads (asset_id, road_name, length_km, surface_type, pothole_count, crack_severity, road_condition, priority) VALUES
(23, 'Main Entrance Boulevard', 1.20, 'Asphalt', 0, 'None', 'Good', 'Low'),
(24, 'University Central Spine Road', 2.10, 'Asphalt', 1, 'Minor', 'Good', 'Low'),
(25, 'Engineering Ring Road East', 1.80, 'Concrete', 3, 'Moderate', 'Moderate', 'Medium'),
(26, 'Hostel Transit Lane', 1.50, 'Asphalt', 9, 'Severe', 'Critical', 'Urgent'),
(27, 'Sports Complex Access Way', 0.90, 'Paver Blocks', 1, 'Minor', 'Moderate', 'Medium'),
(28, 'Workshop Heavy Haul Track', 1.10, 'Concrete', 6, 'Severe', 'Poor', 'High'),
(29, 'Cafeteria Pedestrian Way', 0.60, 'Paver Blocks', 0, 'None', 'Good', 'Low'),
(30, 'Research Park Link Road', 1.40, 'Asphalt', 1, 'Minor', 'Good', 'Low'),
(31, 'South Gate Freight Corridor', 1.30, 'Asphalt', 12, 'Severe', 'Critical', 'Urgent'),
(32, 'Faculty Housing Internal Lane', 0.80, 'Concrete', 1, 'Minor', 'Good', 'Low'),
(33, 'Lake View Circular Drive', 1.70, 'Asphalt', 4, 'Moderate', 'Moderate', 'Medium'),
(34, 'Auditorium North Crescent', 0.70, 'Concrete', 0, 'None', 'Good', 'Low');

-- ---------------------------------------------------------------------
-- 11 MAINTENANCE WORK ORDERS (Streetlights and Roads)
-- ---------------------------------------------------------------------
INSERT INTO maintenance (id, maintenance_code, asset_id, problem, priority, assigned_staff_id, created_date, due_date, status, notes) VALUES
(1, 'MNT-2026-001', 6, 'Luminaire burnt out; driver circuit failed', 'Urgent', 2, '2026-09-10', '2026-09-22', 'In Progress', 'Replacement Philips 70W LED unit requested from warehouse.'),
(2, 'MNT-2026-002', 12, 'Loose wiring causing total power failure at south checkpoint', 'Urgent', 2, '2026-09-11', '2026-09-21', 'Assigned', 'Safety hazard during night shifts. Scheduled bucket truck.'),
(3, 'MNT-2026-003', 26, 'Multiple large potholes near Boys Hostel entrance causing scooter skid risk', 'Urgent', 2, '2026-09-12', '2026-09-24', 'In Progress', 'Cold mix asphalt patching initiated. 4 potholes filled.'),
(4, 'MNT-2026-004', 31, 'Severe surface cracking and aggregate depression along freight road', 'High', 2, '2026-09-13', '2026-09-26', 'Pending', 'Heavy delivery vehicles diverted to auxiliary lane.'),
(9, 'MNT-2026-009', 5, 'Intermittent flicker in LED array and voltage fluctuations', 'High', 2, '2026-09-16', '2026-09-27', 'Pending', 'Check ballast capacitor and neutral ground.'),
(10, 'MNT-2026-010', 20, 'Circuit breaker tripping continuously at substation pole', 'High', 2, '2026-09-17', '2026-09-25', 'Pending', 'High priority electrical inspection needed.'),
(11, 'MNT-2026-011', 28, 'Deep rutting and surface subsidence on workshop access track', 'Medium', 2, '2026-09-17', '2026-09-30', 'Pending', 'Requires leveling and concrete sub-base reinforcment.'),
(15, 'MNT-2026-015', 4, 'Photocell sensor malfunctioning; light remains on in daytime', 'Low', 2, '2026-09-19', '2026-10-05', 'Pending', 'Photocell replacement needed to conserve energy.'),
(16, 'MNT-2026-016', 1, 'Routine quarterly LED cleaning and luminaire check', 'Low', 2, '2026-08-20', '2026-08-22', 'Completed', 'Glass cleaned, luminaire test passed at 98% efficiency.'),
(17, 'MNT-2026-017', 2, 'Tightened terminal screws and checked waterproof casing', 'Low', 2, '2026-08-15', '2026-08-16', 'Completed', 'Weatherproof seal intact.'),
(18, 'MNT-2026-018', 23, 'Kerb repainting and minor sealant application on road edge', 'Low', 2, '2026-08-10', '2026-08-12', 'Completed', 'Reflective yellow marking completed.');

-- ---------------------------------------------------------------------
-- 10 PREDICTIVE ALERTS (Streetlights and Roads)
-- ---------------------------------------------------------------------
INSERT INTO alerts (id, asset_id, alert_type, problem, risk_level, recommended_action, status, created_at) VALUES
(1, 6, 'Critical', 'Streetlight SL-006 is predicted to fail soon due to rapid voltage drops and aging driver.', 'High Risk', 'Replace driver capacitor and LED module within 48 hours.', 'In Progress', '2026-09-18 10:15:00'),
(2, 12, 'Critical', 'Streetlight SL-012 power supply intermittent; high failure probability in 3 days.', 'High Risk', 'Dispatch bucket truck for cable reconnection.', 'Pending', '2026-09-19 08:30:00'),
(3, 20, 'Critical', 'Streetlight SL-020 electrical surge risk near main substation yard.', 'High Risk', 'Inspect surge protection unit and transformer junction.', 'Pending', '2026-09-19 14:20:00'),
(4, 26, 'Critical', 'Road RD-004 severe surface deterioration index exceeded critical threshold (9 potholes).', 'High Risk', 'Initiate emergency bitumen patching and place warning cones.', 'In Progress', '2026-09-17 11:45:00'),
(5, 31, 'Critical', 'Road RD-009 freight route fatigue breakdown predicted within 7 days.', 'High Risk', 'Overlay 50mm bitumen binder course and restrict overload trucks.', 'Pending', '2026-09-18 16:00:00'),
(10, 5, 'Warning', 'Streetlight SL-005 flickering pattern indicates capacitor degradation.', 'Medium Risk', 'Schedule driver replacement during upcoming routine cycle.', 'Pending', '2026-09-18 19:25:00'),
(11, 10, 'Warning', 'Streetlight SL-010 optical luminaire degradation (>40% lumen loss).', 'Medium Risk', 'Clean refractor glass and test ballast voltage.', 'Pending', '2026-09-17 18:10:00'),
(12, 18, 'Warning', 'Streetlight SL-018 wiring resistance fluctuation in faculty sector.', 'Medium Risk', 'Inspect underground cable conduit for moisture ingress.', 'Pending', '2026-09-16 20:05:00'),
(13, 28, 'Warning', 'Road RD-006 surface micro-cracks spreading under heavy load.', 'Medium Risk', 'Apply bitumen emulsion crack seal before monsoon.', 'Pending', '2026-09-15 15:50:00'),
(18, 4, 'Maintenance', 'Streetlight SL-004 dusk-to-dawn photocell sensor timer drift.', 'Low Risk', 'Recalibrate digital optical sensor.', 'Pending', '2026-09-15 17:00:00');

-- ---------------------------------------------------------------------
-- CAMPUS SURVEY RESPONSES
-- ---------------------------------------------------------------------
INSERT INTO survey_responses (survey_id, respondent_name, respondent_role, streetlights_working, streetlights_flickering, roads_potholes, roads_maintenance_needed, water_leakage_observed, water_supply_regular, drainage_blocked, drainage_flow_ok, maintenance_satisfaction, maintenance_timely, ai_monitoring_useful, ai_would_use, comments) VALUES
(1, 'Aarav Sharma', 'Student', 'Mostly', 'A Few', 'Minor', 'Yes', 'None', 'Yes', 'None', 'Good', 4, 'Usually', 'Extremely', 'Definitely', 'Hostel road potholes need quick fixing, especially near Block 2.'),
(1, 'Pooja Reddy', 'Student', 'Yes', 'None', 'None', 'No', 'None', 'Yes', 'None', 'Good', 5, 'Always', 'Extremely', 'Definitely', 'Streetlights near the library and main gate are bright and safe at night.'),
(1, 'Dr. M. Srinivasan', 'Faculty', 'Mostly', 'A Few', 'Minor', 'Yes', 'None', 'Yes', 'None', 'Good', 4, 'Usually', 'Very', 'Definitely', 'AI predictive alerts will save significant college maintenance expenditure.'),
(1, 'Rohan Verma', 'Student', 'No', 'Many', 'Severe', 'Yes', 'None', 'Yes', 'None', 'Good', 2, 'Rarely', 'Extremely', 'Definitely', 'Boys hostel road needs repaving.'),
(1, 'Sneha Patel', 'Student', 'Mostly', 'A Few', 'Minor', 'No', 'None', 'Yes', 'None', 'Good', 4, 'Usually', 'Extremely', 'Definitely', 'A live status map makes it easy to see which routes are well-lit.'),
(1, 'Prof. Anita Deshmukh', 'Faculty', 'Yes', 'None', 'None', 'No', 'None', 'Yes', 'None', 'Good', 5, 'Always', 'Very', 'Definitely', 'Very impressive initiative for digital smart campus management.'),
(1, 'Kiran Kumar', 'Staff', 'Mostly', 'A Few', 'Minor', 'Yes', 'None', 'Yes', 'None', 'Good', 3, 'Usually', 'Extremely', 'Definitely', 'Field workers would benefit from direct mobile notifications.'),
(1, 'Vikram Malhotra', 'Visitor', 'Yes', 'None', 'None', 'No', 'None', 'Yes', 'None', 'Good', 4, 'Usually', 'Extremely', 'Probably', 'Campus is very clean, signage and lighting are good.'),
(1, 'Ananya Iyer', 'Student', 'Mostly', 'A Few', 'Minor', 'Yes', 'None', 'Yes', 'None', 'Good', 4, 'Usually', 'Extremely', 'Definitely', 'Road near the sports pavilion needs speed breakers and light inspection.'),
(1, 'Suresh Babu', 'Staff', 'No', 'Many', 'Severe', 'Yes', 'None', 'Yes', 'None', 'Good', 2, 'Rarely', 'Extremely', 'Definitely', 'Streetlight pole 06 near sports ground needs lamp replacement.'),
(1, 'Neha Gupta', 'Student', 'Yes', 'None', 'None', 'No', 'None', 'Yes', 'None', 'Good', 5, 'Always', 'Extremely', 'Definitely', 'Great to see automated infrastructure tracking implemented.'),
(1, 'Arjun Nair', 'Student', 'Mostly', 'A Few', 'Minor', 'No', 'None', 'Yes', 'None', 'Good', 4, 'Usually', 'Very', 'Definitely', 'Adding streetlights directly from the map is super convenient!');


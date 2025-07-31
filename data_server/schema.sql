-- Main data table
CREATE TABLE IF NOT EXISTS main_data (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    temperature_1 REAL,
    temperature_2 REAL,
    temperature_3 REAL,
    temperature_4 REAL,
    ph REAL,
    battery_level REAL,
    tds REAL,
    turbidity REAL
);

-- Wake data table  
CREATE TABLE IF NOT EXISTS wake_data (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    -- Rotation data separated into individual columns
    yaw REAL,
    pitch REAL,
    roll REAL,
    ax REAL,
    ay REAL,
    az REAL,
    gx REAL,
    gy REAL,
    gz REAL,
    qx REAL,
    qy REAL,
    qz REAL,
    qw REAL,
    lax REAL,
    lay REAL,
    laz REAL,
    hydrophone_reading REAL,
    water_level REAL
);

-- Create indexes for timestamp queries
CREATE INDEX IF NOT EXISTS idx_main_timestamp ON main_data(timestamp);
CREATE INDEX IF NOT EXISTS idx_wake_timestamp ON wake_data(timestamp); 
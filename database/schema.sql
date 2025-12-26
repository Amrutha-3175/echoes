-- =========================
-- Database: Echoes
-- =========================
-- Drop existing tables if needed (optional during development)
-- DROP DATABASE echoes;
-- CREATE DATABASE echoes;
-- USE echoes;

-- =========================
-- USERS TABLE
-- =========================
CREATE TABLE users (
    user_id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,

    -- Password constraints:
    -- Minimum 6 characters AND must contain at least one number (0–9)
    CHECK (CHAR_LENGTH(password) >= 6),
    CHECK (password REGEXP '[0-9]')
);

-- =========================
-- EMOTIONS TABLE
-- =========================
CREATE TABLE emotions (
    emotion_id INT PRIMARY KEY AUTO_INCREMENT,
    emotion_name VARCHAR(50) NOT NULL
);

-- =========================
-- MEMORIES TABLE
-- =========================
CREATE TABLE memories (
    memory_id INT PRIMARY KEY AUTO_INCREMENT,
    title VARCHAR(200),
    content TEXT NOT NULL,
    memory_date DATE NOT NULL,

    -- Media storage (paths, not blobs)
    image_path VARCHAR(255),
    audio_path VARCHAR(255),

    user_id INT NOT NULL,
    emotion_id INT NOT NULL,

    FOREIGN KEY (user_id)
        REFERENCES users(user_id)
        ON DELETE CASCADE,

    FOREIGN KEY (emotion_id)
        REFERENCES emotions(emotion_id)
        ON DELETE RESTRICT
);

-- =========================
-- TAGS TABLE
-- =========================
CREATE TABLE tags (
    tag_id INT PRIMARY KEY AUTO_INCREMENT,
    tag_name VARCHAR(50) UNIQUE NOT NULL
);

-- =========================
-- MANY-TO-MANY LINK TABLE
-- =========================
CREATE TABLE memory_tags (
    memory_id INT NOT NULL,
    tag_id INT NOT NULL,

    PRIMARY KEY (memory_id, tag_id),

    FOREIGN KEY (memory_id)
        REFERENCES memories(memory_id)
        ON DELETE CASCADE,

    FOREIGN KEY (tag_id)
        REFERENCES tags(tag_id)
        ON DELETE CASCADE
);

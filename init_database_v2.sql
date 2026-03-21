-- Initialize Git Analysis Database Schema
-- This script creates the database and table for storing git commit analysis data

-- Create database if it doesn't exist
IF NOT EXISTS (SELECT * FROM sys.databases WHERE name = 'GitAnalysis')
BEGIN
    CREATE DATABASE GitAnalysis;
END
GO

USE GitAnalysis;
GO

-- Create commits table if it doesn't exist
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[commit_files]') AND type in (N'U'))
BEGIN
    CREATE TABLE [dbo].[commit_files] (
        [id] INT IDENTITY(1,1) PRIMARY KEY,
        [repository] NVARCHAR(255) NOT NULL,
        [commit_hash] NVARCHAR(40) NOT NULL,
        [date] DATETIME2 NOT NULL,
        [message] NVARCHAR(MAX),
        [file_path] NVARCHAR(MAX),
        [additions] INT NOT NULL DEFAULT 0,
        [deletions] INT NOT NULL DEFAULT 0,
        [modifications] INT NOT NULL DEFAULT 0,
        [nloc_additions] INT NOT NULL DEFAULT 0,
        [nloc_deletions] INT NOT NULL DEFAULT 0,
        [nloc_modifications] INT NOT NULL DEFAULT 0,
        [created_at] DATETIME2 DEFAULT GETDATE(),
    );
    
    -- Create indexes for better query performance
    CREATE INDEX IX_commits_repository ON [dbo].[commit_files](repository);
    CREATE INDEX IX_commits_date ON [dbo].[commit_files](date);
    CREATE INDEX IX_commits_repository_date ON [dbo].[commit_files](repository, date);
END
GO

-- Display the table structure
SELECT 
    COLUMN_NAME, 
    DATA_TYPE, 
    CHARACTER_MAXIMUM_LENGTH, 
    IS_NULLABLE
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_NAME = 'commit_files'
ORDER BY ORDINAL_POSITION;
GO

PRINT 'Database schema initialized successfully!';
GO

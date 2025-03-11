# DocBrain Release Notes

This document provides detailed information about changes and improvements in each release of DocBrain.

## v1.1.0 (Current Release)

**Role-Based Access Control & Knowledge Base Sharing**

### Enhanced Permission System
- Implemented comprehensive role-based access control (RBAC)
- Added granular permissions for knowledge base, document, and user management
- Created three user roles: Admin, Owner, and User
- Defined specific permission sets for each role to ensure proper access control
- Implemented permission checking middleware for API endpoints

### Knowledge Base Sharing
- Added ability for Owner and Admin users to share knowledge bases with specific users
- Implemented dedicated "shared-with-me" endpoint for users to access knowledge bases shared with them
- Created APIs to manage sharing relationships (add/remove users, list shared users)
- Added database schema support for sharing relationships between users and knowledge bases

### Access Control Refinements
- Admin users can view all knowledge bases in the system
- Owner users can only view knowledge bases they created
- Regular users can only access knowledge bases explicitly shared with them
- Regular users receive empty lists instead of permission errors when accessing unshared resources
- Permission checks integrated throughout API endpoints

### User Management
- Enhanced user listing capabilities with role-based restrictions
- Admin users can manage all users in the system
- Owner users can view user information but not modify users
- Regular users cannot access user management features
- Updated API documentation to clarify role-based behaviors

### API Improvements
- Updated API response schemas to include role information
- Clarified behavior of list endpoints based on user roles
- Improved error handling for permission-related issues
- Ensured consistent responses across all endpoints

## v1.0.0 (Initial Release)

### Core RAG Functionality
- Document ingestion and chunking pipeline
- Vector storage integration (Pinecone)
- Basic retrieval-augmented generation
- Document processing for various file formats
- Context window optimization

### Query Routing
- Intelligent query classification system
- Automatic routing between RAG and TAG systems
- Query type detection for different data sources
- Confidence scoring for routing decisions
- Fallback mechanisms for ambiguous queries

### Table Augmented Generation (TAG)
- SQL generation for tabular data queries
- CSV/Excel file support with automatic schema detection
- Query execution against stored tables
- Result formatting and presentation
- Explanation generation for query results

### System Architecture
- Modular design for component interchangeability
- REST API for all functionality
- Async processing for document ingestion
- Background workers for compute-intensive tasks
- Comprehensive logging and error handling

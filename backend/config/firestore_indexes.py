"""
Firestore Index Requirements for OMTX-Hub Performance Optimization

These composite indexes are CRITICAL for My Results performance and must be created
in the Firestore console before deploying the optimized queries.

Author: OMTX Engineering
Date: 2025-08-04
"""

# Required Composite Indexes for Performance

REQUIRED_INDEXES = [
    {
        "collection": "jobs",
        "fields": [
            {"field": "user_id", "order": "ASCENDING"},
            {"field": "status", "order": "ASCENDING"},
            {"field": "created_at", "order": "DESCENDING"}
        ],
        "description": "User results filtered by status, sorted by date"
    },
    {
        "collection": "jobs",
        "fields": [
            {"field": "user_id", "order": "ASCENDING"},
            {"field": "model_name", "order": "ASCENDING"},
            {"field": "created_at", "order": "DESCENDING"}
        ],
        "description": "User results filtered by model, sorted by date"
    },
    {
        "collection": "jobs",
        "fields": [
            {"field": "status", "order": "ASCENDING"},
            {"field": "created_at", "order": "DESCENDING"}
        ],
        "description": "All results filtered by status (for monitoring)"
    },
    {
        "collection": "jobs",
        "fields": [
            {"field": "batch_parent_id", "order": "ASCENDING"},
            {"field": "batch_index", "order": "ASCENDING"}
        ],
        "description": "Batch children lookup by parent"
    },
    {
        "collection": "jobs",
        "fields": [
            {"field": "job_type", "order": "ASCENDING"},
            {"field": "created_at", "order": "DESCENDING"}
        ],
        "description": "Jobs filtered by type (single, batch_parent, batch_child)"
    },
    {
        "collection": "jobs",
        "fields": [
            {"field": "user_id", "order": "ASCENDING"},
            {"field": "job_type", "order": "ASCENDING"},
            {"field": "created_at", "order": "DESCENDING"}
        ],
        "description": "User jobs filtered by type"
    },
    {
        "collection": "jobs",
        "fields": [
            {"field": "user_id", "order": "ASCENDING"},
            {"field": "created_at", "order": "ASCENDING"},
            {"field": "__name__", "order": "ASCENDING"}
        ],
        "description": "User jobs with document name for pagination cursors"
    }
]

# Single Field Indexes (usually auto-created by Firestore)
SINGLE_FIELD_INDEXES = [
    "created_at",
    "status",
    "model_name",
    "job_type",
    "user_id",
    "batch_parent_id",
    "updated_at"
]


def generate_firestore_console_url(project_id: str) -> str:
    """Generate URL to create indexes in Firestore console"""
    return f"https://console.firebase.google.com/project/{project_id}/firestore/indexes"


def generate_gcloud_commands(project_id: str) -> list[str]:
    """Generate gcloud commands to create indexes programmatically"""
    commands = []
    
    for index in REQUIRED_INDEXES:
        fields_args = []
        for field in index["fields"]:
            order = "ascending" if field["order"] == "ASCENDING" else "descending"
            fields_args.append(f"{field['field']},{order}")
        
        cmd = (
            f"gcloud firestore indexes composite create "
            f"--collection-group={index['collection']} "
            f"--field-config=" + ",".join(fields_args) + " "
            f"--project={project_id}"
        )
        commands.append(cmd)
    
    return commands


def validate_index_coverage(query_fields: list[str], order_by: str = None) -> bool:
    """
    Validate if a query is covered by our indexes
    
    Args:
        query_fields: List of fields used in where clauses
        order_by: Field used for ordering
        
    Returns:
        bool: True if query is covered by an index
    """
    query_set = set(query_fields)
    if order_by:
        query_set.add(order_by)
    
    for index in REQUIRED_INDEXES:
        index_fields = {f["field"] for f in index["fields"]}
        if query_set.issubset(index_fields):
            return True
    
    return len(query_set) <= 1  # Single field queries don't need composite indexes


# Performance tips for developers
PERFORMANCE_TIPS = """
Firestore Query Performance Best Practices:

1. Always use composite indexes for queries with multiple fields
2. Order matters in composite indexes - most selective fields first
3. Use cursor-based pagination instead of offset for large datasets
4. Limit query results to what's needed (default to 20-50 items)
5. Cache frequently accessed data with appropriate TTL
6. Use select() to fetch only required fields for list views
7. Batch reads when fetching multiple documents by ID

Example optimized query:
    query = db.collection('jobs')
        .where('user_id', '==', user_id)
        .where('status', '==', 'completed')
        .order_by('created_at', direction=firestore.Query.DESCENDING)
        .limit(20)
"""

if __name__ == "__main__":
    # Helper script to print index creation commands
    import sys
    
    if len(sys.argv) > 1:
        project_id = sys.argv[1]
        print(f"Firestore Index Creation Commands for project: {project_id}\n")
        print(f"Console URL: {generate_firestore_console_url(project_id)}\n")
        print("CLI Commands:")
        for cmd in generate_gcloud_commands(project_id):
            print(f"\n{cmd}")
    else:
        print("Usage: python firestore_indexes.py <project-id>")
        print("\nRequired Indexes:")
        for idx in REQUIRED_INDEXES:
            print(f"\n- {idx['description']}")
            for field in idx['fields']:
                print(f"  • {field['field']} ({field['order']})")
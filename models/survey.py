from database import query_db, execute_db

def get_survey_responses(limit=50):
    """
    Retrieves recent campus infrastructure survey responses submitted by students and faculty.
    
    How it works:
    - Selects all survey answer fields from `survey_responses`.
    - Orders by primary key ID descending (newest submissions first).
    - Limits to specified batch size (default: 50).
    
    Args:
        limit (int, optional): Maximum records to retrieve.
        
    Returns:
        list[dict]: List of survey response records.
    """
    query = """
        SELECT id, respondent_name, respondent_role,
               streetlights_working, streetlights_flickering,
               roads_potholes, roads_maintenance_needed,
               water_leakage_observed, water_supply_regular,
               drainage_blocked, drainage_flow_ok,
               maintenance_satisfaction, maintenance_timely,
               ai_monitoring_useful, ai_would_use,
               comments, created_at
        FROM survey_responses
        ORDER BY id DESC
    """
    if limit:
        query += f" LIMIT {int(limit)}"
    query += ";"
    return query_db(query)

def submit_survey_response(data):
    """
    Inserts a newly submitted community infrastructure survey questionnaire response into database.
    
    How it works:
    1. Extracts answers across 6 core infrastructure sections:
       - Streetlights (working state, flickering/broken poles).
       - Roads (potholes, resurfacing needed).
       - Water pipelines (leakage observed, regularity).
       - Drainage (blockages, overflow conditions).
       - Maintenance satisfaction (1-5 star scale, timeliness).
       - AI system perception (usefulness, willingness to adopt).
    2. Performs a safe parameterized INSERT into `survey_responses`.
    3. Returns the auto-generated response ID.
    
    Args:
        data (dict): Key-value pairs submitted from the survey form or API.
        
    Returns:
        int: The primary key ID of the inserted survey response.
    """
    return execute_db(
        """INSERT INTO survey_responses (
            survey_id, respondent_name, respondent_role,
            streetlights_working, streetlights_flickering,
            roads_potholes, roads_maintenance_needed,
            water_leakage_observed, water_supply_regular,
            drainage_blocked, drainage_flow_ok,
            maintenance_satisfaction, maintenance_timely,
            ai_monitoring_useful, ai_would_use, comments
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        );""",
        (
            int(data.get('survey_id', 1)),
            data.get('respondent_name', 'Anonymous Student'),
            data.get('respondent_role', 'Student'),
            data.get('streetlights_working', 'Yes'),
            data.get('streetlights_flickering', 'None'),
            data.get('roads_potholes', 'None'),
            data.get('roads_maintenance_needed', 'No'),
            data.get('water_leakage_observed', 'None'),
            data.get('water_supply_regular', 'Yes'),
            data.get('drainage_blocked', 'None'),
            data.get('drainage_flow_ok', 'Good'),
            int(data.get('maintenance_satisfaction', 4)),
            data.get('maintenance_timely', 'Usually'),
            data.get('ai_monitoring_useful', 'Extremely'),
            data.get('ai_would_use', 'Definitely'),
            data.get('comments', '')
        ),
        return_id=True
    )

def get_survey_analytics():
    """
    Calculates statistical distributions across all survey submissions for Chart.js charts.
    
    How it works:
    1. Fetches all records from `survey_responses`.
    2. Computes Average Satisfaction Score (1.0 - 5.0).
    3. Computes AI Endorsement Percentage (% of respondents answering 'Extremely' or 'Very').
    4. Aggregates distributions:
       - `ai_sentiment`: Count breakdown of AI perceived utility.
       - `satisfaction_dist`: 1 to 5 Star counts for the satisfaction bar chart.
       - `infrastructure_issues`: Counts of flagged flickering poles, potholes, leaks, and blocked drains.
       - `respondent_roles`: Count of responses by Student, Faculty, Staff, and Visitors.
       
    Returns:
        dict: Aggregated statistical payload ready for Chart.js rendering.
    """
    responses = query_db("SELECT * FROM survey_responses;")
    total_responses = len(responses)
    if total_responses == 0:
        return {
            'total_responses': 0,
            'avg_satisfaction': 0,
            'ai_useful_pct': 0,
            'ai_sentiment': {},
            'satisfaction_dist': {},
            'infrastructure_issues': {},
            'respondent_roles': {}
        }
        
    avg_sat = round(sum(r['maintenance_satisfaction'] for r in responses) / total_responses, 1)
    
    # AI usefulness breakdown
    ai_useful_count = sum(1 for r in responses if r['ai_monitoring_useful'] in ('Extremely', 'Very'))
    ai_useful_pct = round((ai_useful_count / total_responses) * 100, 1)
    
    ai_sentiment = {'Extremely': 0, 'Very': 0, 'Somewhat': 0, 'Not Useful': 0}
    for r in responses:
        val = r.get('ai_monitoring_useful')
        if val in ai_sentiment:
            ai_sentiment[val] += 1
            
    # Satisfaction rating distribution (1 to 5)
    sat_dist = {'1 Star': 0, '2 Stars': 0, '3 Stars': 0, '4 Stars': 0, '5 Stars': 0}
    for r in responses:
        val = r.get('maintenance_satisfaction', 4)
        key = f"{val} Star" if val == 1 else f"{val} Stars"
        if key in sat_dist:
            sat_dist[key] += 1
            
    # Issues detected in surveys (Focused on Streetlights and Roads)
    issues = {
        'Streetlights Flickering': sum(1 for r in responses if r.get('streetlights_flickering') != 'None'),
        'Road Potholes Reported': sum(1 for r in responses if r.get('roads_potholes') != 'None'),
        'Lighting Outages': sum(1 for r in responses if r.get('streetlights_working') != 'Yes'),
        'Road Resurfacing Needed': sum(1 for r in responses if r.get('roads_maintenance_needed') == 'Yes')
    }
    
    # Roles distribution
    roles = {}
    for r in responses:
        role = r.get('respondent_role', 'Other')
        roles[role] = roles.get(role, 0) + 1
        
    return {
        'total_responses': total_responses,
        'avg_satisfaction': avg_sat,
        'ai_useful_pct': ai_useful_pct,
        'ai_sentiment': ai_sentiment,
        'satisfaction_dist': sat_dist,
        'infrastructure_issues': issues,
        'respondent_roles': roles
    }

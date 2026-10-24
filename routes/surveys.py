from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from routes.auth import login_required
from models.survey import submit_survey_response, get_survey_responses, get_survey_analytics

surveys_bp = Blueprint('surveys', __name__)

@surveys_bp.route('/surveys')
@login_required
def surveys_page():
    """
    Endpoint: /surveys (GET)
    
    Purpose:
        Serves the Campus Community Infrastructure Feedback & Satisfaction Survey portal.
        Allows students, faculty, and administrative staff to submit real-time condition reports
        and reviews of campus streetlights, road surfaces, water delivery, and drainage.
        Displays aggregated satisfaction analytics and the latest community response stream.
        
    Context Variables Passed to Template:
        analytics (dict): Aggregated percentage metrics (satisfaction score, streetlight working rate, etc.).
        responses (list): 25 most recent survey feedback entries.
        
    Returns:
        HTML template render ('surveys.html').
    """
    # Step 1: Compute real-time survey analytical metrics
    analytics = get_survey_analytics()
    
    # Step 2: Fetch the 25 most recent survey submissions
    responses = get_survey_responses(limit=25)
    
    # Step 3: Render the interactive survey feedback view
    return render_template(
        'surveys.html',
        analytics=analytics,
        responses=responses
    )

@surveys_bp.route('/api/surveys', methods=['POST'])
@login_required
def api_submit_survey():
    """
    Endpoint: /api/surveys (POST)
    
    Purpose:
        Receives and records campus infrastructure survey submissions from students, faculty,
        or staff members.
        
    Request Payload (JSON or Form Data):
        respondent_name (str): Name of the survey participant.
        respondent_role (str): 'Student', 'Faculty', 'Staff', or 'Visitor'.
        streetlights_working (str): 'Yes', 'No', or 'Partially'.
        roads_potholes (str): 'Good', 'Few Potholes', or 'Severe Potholes'.
        water_supply_regular (str): 'Yes' or 'No'.
        drainage_blocked (str): 'Clean', 'Partially Blocked', or 'Overflowing'.
        maintenance_satisfaction (int): Numerical rating from 1 to 5.
        ai_monitoring_useful (str): 'Yes' or 'No'.
        comments (str, optional): Qualitative suggestions or issue reports.
        
    Returns:
        JSON Response with new response ID (201) or HTTP 302 redirect for browser forms.
    """
    # Step 1: Parse survey submission from JSON body or form
    data = request.get_json() if request.is_json else request.form.to_dict()
    
    # Step 2: Persist survey response into database
    try:
        resp_id = submit_survey_response(data)
        if request.is_json:
            return jsonify({'success': True, 'id': resp_id, 'message': 'Survey response recorded successfully!'}), 201
            
        flash('Thank you! Your campus infrastructure feedback has been recorded.', 'success')
        return redirect(url_for('surveys.surveys_page'))
    except Exception as e:
        if request.is_json:
            return jsonify({'error': str(e)}), 500
        flash(f'Error submitting survey: {e}', 'danger')
        return redirect(url_for('surveys.surveys_page'))

@surveys_bp.route('/api/surveys/analytics', methods=['GET'])
@login_required
def api_survey_analytics():
    """
    Endpoint: /api/surveys/analytics (GET)
    
    Purpose:
        REST API endpoint returning statistical summary of community survey responses
        for charting and analytics widgets.
        
    Returns:
        JSON Response: Dictionary containing:
            - total_responses: Count of collected surveys
            - avg_satisfaction: Average rating (1.0 to 5.0)
            - streetlight_ok_percent: Percentage reporting operational lighting
            - water_regular_percent: Percentage reporting normal water supply
            - pothole_complaint_percent: Percentage noting road deterioration
            - drainage_block_percent: Percentage reporting drainage overflow
    """
    # Step 1: Retrieve analytics summary from survey model
    analytics_data = get_survey_analytics()
    
    # Step 2: Return JSON response
    return jsonify(analytics_data)

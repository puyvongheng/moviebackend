from flask import Flask, request, jsonify
import json
import os
from werkzeug.security import generate_password_hash, check_password_hash
import uuid
import logging
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # This will allow all origins (for development)


# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Path to JSON database
DB_FILE = 'users.json'

# Initialize JSON database if it doesn't exist
def init_db():
    if not os.path.exists(DB_FILE):
        logging.info(f"Database file '{DB_FILE}' not found. Initializing new DB.")
        with open(DB_FILE, 'w') as f:
            json.dump({"users": {}}, f, indent=2)

# Read users data from JSON
def read_users_data():
    try:
        with open(DB_FILE, 'r') as f:
            data = json.load(f)
            if "users" not in data:
                data["users"] = {}
            return data
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logging.error(f"Error reading database file '{DB_FILE}': {e}. Returning initial structure.")
        return {"users": {}}

# Write users data to JSON
def write_users_data(data):
    try:
        with open(DB_FILE, 'w') as f:
            json.dump(data, f, indent=2)
    except IOError as e:
        logging.error(f"Error writing to database file '{DB_FILE}': {e}")

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    email = data.get('email')
    username = data.get('username')
    password = data.get('password')
    img_url = data.get('img_url', '')  # Default to empty string if not provided

    if not all([email, username, password]):
        return jsonify({'error': 'Missing required fields'}), 400

    users_data = read_users_data()
    users = users_data.get('users', {})

    # Check if email is already registered
    for user in users.values():
        if user['email'] == email:
            return jsonify({'error': 'Email already registered'}), 400

    if '@' not in email or '.' not in email:
        return jsonify({'error': 'Invalid email format'}), 400

    if len(password) < 6:
        return jsonify({'error': 'Password must be at least 6 characters'}), 400

    user_id = str(uuid.uuid4())

    users[user_id] = {
        'id': user_id,
        'email': email,
        'username': username,
        'img_url': img_url,
        'password': generate_password_hash(password),
        'favorites': [],
        'watchlist': [],
        'purchases': []
    }

    users_data['users'] = users
    write_users_data(users_data)

    logging.info(f"User '{username}' with email '{email}' registered successfully (ID: {user_id}).")
    return jsonify({'message': 'Registration successful', 'username': username, 'user_id': user_id}), 201

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    
    app.logger.debug(f'Login attempt for email: {email}, Cookies: {request.cookies}')

    if not all([email, password]):
        return jsonify({'error': 'Missing required fields'}), 400

    users_data = read_users_data()
    users = users_data.get('users', {})

    user = None
    user_id = None
    for uid, u in users.items():
        if u['email'] == email:
            user = u
            user_id = uid
            break

    if not user or not check_password_hash(user['password'], password):
        logging.warning(f"Login failed for email '{email}': Invalid email or password.")
        return jsonify({'error': 'Invalid email or password'}), 401

    logging.info(f"User '{user['username']}' (ID: {user_id}) logged in successfully.")
    return jsonify({'message': 'Login successful', 'username': user['username'], 'user_id': user_id}), 200

@app.route('/logout', methods=['POST'])
def logout():
    app.logger.debug(f'Logout attempt, Cookies: {request.cookies}')
    logging.info("Logout requested. No session to clear in stateless backend.")
    return jsonify({'message': 'Logged out successfully'}), 200

@app.route('/account', methods=['GET'])
def account():
    app.logger.debug(f'Account request, Cookies: {request.cookies}')
    user_id = request.args.get('user_id')

    if not user_id:
        logging.info("Account data requested without user_id. Returning Guest data.")
        return jsonify({
            'username': 'Guest',
            'img_url': '',
            'isLoggedIn': False,
            'favorites': [],
            'watchlist': [],
            'purchases': []
        }), 200

    users_data = read_users_data()
    users = users_data.get('users', {})
    user = users.get(user_id)

    if not user:
        logging.warning(f"Account request for user ID {user_id} not found in DB.")
        return jsonify({
            'username': 'Guest',
            'img_url': '',
            'isLoggedIn': False,
            'favorites': [],
            'watchlist': [],
            'purchases': []
        }), 200

    logging.info(f"Account data requested for user '{user['username']}' (ID: {user_id}).")
    return jsonify({
        'username': user['username'],
        'img_url': user['img_url'],
        'isLoggedIn': True,
        'favorites': user.get('favorites', []),
        'watchlist': user.get('watchlist', []),
        'purchases': user.get('purchases', [])
    }), 200

@app.route('/favorites', methods=['POST'])
def toggle_favorite():
    app.logger.debug(f'Favorites request, Cookies: {request.cookies}')
    
    data = request.get_json()
    movie_id = data.get('movie_id')
    user_id = data.get('user_id')

    if not movie_id:
        logging.warning("Missing movie_id in favorites request.")
        return jsonify({'error': 'Missing movie_id'}), 400
    if not user_id:
        logging.warning("Missing user_id in favorites request.")
        return jsonify({'error': 'Missing user_id'}), 400

    users_data = read_users_data()
    users = users_data.get('users', {})
    user = users.get(user_id)

    if not user:
        logging.error(f"User ID {user_id} not found in DB during favorites toggle.")
        return jsonify({'error': 'User not found. Please log in again.'}), 404

    favorites = user.get('favorites', [])
    action = ''
    if movie_id in favorites:
        favorites.remove(movie_id)
        action = 'removed'
    else:
        favorites.append(movie_id)
        action = 'added'
    
    user['favorites'] = favorites
    users_data['users'] = users
    write_users_data(users_data)
    logging.info(f"Movie {movie_id} {action} to favorites for user '{user.get('username')}' (ID: {user_id}).")
    return jsonify({'message': f'Movie {action} to favorites'}), 200

@app.route('/watchlist', methods=['POST'])
def toggle_watchlist():
    # app.logger.debug(f'Watchlist request, Cookies: {request.cookies}')
    
    data = request.get_json()
    print(data)
    movie_id = data.get('movie_id')
    user_id = data.get('user_id')

    if not movie_id:
        logging.warning("Missing movie_id in watchlist request.")
        return jsonify({'error': 'Missing movie_id'}), 400
    if not user_id:
        logging.warning("Missing user_id in watchlist request.")
        return jsonify({'error': 'Missing user_id'}), 400

    users_data = read_users_data()
    users = users_data.get('users', {})
    user = users.get(user_id)

    if not user:
        logging.error(f"User ID {user_id} not found in DB during watchlist toggle.")
        return jsonify({'error': 'User not found. Please log in again.'}), 404

    watchlist = user.get('watchlist', [])
    action = ''
    if movie_id in watchlist:
        watchlist.remove(movie_id)
        action = 'removed'
    else:
        watchlist.append(movie_id)
        action = 'added'
    
    user['watchlist'] = watchlist
    users_data['users'] = users
    write_users_data(users_data)
    logging.info(f"Movie {movie_id} {action} to watchlist for user '{user.get('username')}' (ID: {user_id}).")
    return jsonify({'message': f'Movie {action} to watchlist'}), 200

@app.route('/purchases', methods=['POST'])
def add_purchase():
    app.logger.debug(f'Purchases request, Cookies: {request.cookies}')
    
    data = request.get_json()
    movie_id = data.get('movie_id')
    user_id = data.get('user_id')

    if not movie_id:
        logging.warning("Missing movie_id in purchases request.")
        return jsonify({'error': 'Missing movie_id'}), 400
    if not user_id:
        logging.warning("Missing user_id in purchases request.")
        return jsonify({'error': 'Missing user_id'}), 400

    users_data = read_users_data()
    users = users_data.get('users', {})
    user = users.get(user_id)

    if not user:
        logging.error(f"User ID {user_id} not found in DB during purchase add.")
        return jsonify({'error': 'User not found. Please log in again.'}), 404

    purchases = user.get('purchases', [])
    if movie_id in purchases:
        logging.info(f"User '{user.get('username')}' (ID: {user_id}) attempted to repurchase movie {movie_id}.")
        return jsonify({'error': 'Movie already purchased'}), 400

    purchases.append(movie_id)
    user['purchases'] = purchases
    users_data['users'] = users
    write_users_data(users_data)
    logging.info(f"Movie {movie_id} purchased successfully by user '{user.get('username')}' (ID: {user_id}).")
    return jsonify({'message': 'Movie purchased successfully'}), 200


@app.route('/my_userwatchlist', methods=['GET'])
def my_userwatchlist():
    app.logger.debug(f'My user watchlist request, Cookies: {request.cookies}')
    user_id = request.args.get('user_id')
    if not user_id:
        logging.info("My user watchlist requested without user_id. Returning empty lists.")
        return jsonify({
            'favorites': [],
            'watchlist': [],
            'purchases': []
        }), 200
    users_data = read_users_data()
    users = users_data.get('users', {})
    user = users.get(user_id)
    if not user:
        logging.warning(f"My user watchlist request for user ID {user_id} not found in DB.")
        return jsonify({
            'favorites': [],
            'watchlist': [],
            'purchases': []
        }), 200
    logging.info(f"My user watchlist data requested for user '{user['username']}' (ID: {user_id}).")
    return jsonify({
        'favorites': user.get('favorites', []),
        'watchlist': user.get('watchlist', []),
        'purchases': user.get('purchases', [])
    }), 200



@app.route('/update_profile', methods=['POST'])
def update_profile():
    app.logger.debug(f'Update profile request, Cookies: {request.cookies}')
    data = request.get_json()
    user_id = data.get('user_id')
    img_url = data.get('img_url')

    if not user_id:
        logging.warning("Missing user_id in update profile request.")
        return jsonify({'error': 'Missing user_id'}), 400
    if not img_url:
        logging.warning("Missing img_url in update profile request.")
        return jsonify({'error': 'Missing img_url'}), 400

    users_data = read_users_data()
    users = users_data.get('users', {})
    user = users.get(user_id)

    if not user:
        logging.error(f"User ID {user_id} not found in DB during profile update.")
        return jsonify({'error': 'User not found. Please log in again.'}), 404

    user['img_url'] = img_url
    users_data['users'] = users
    write_users_data(users_data)
    logging.info(f"Profile updated with new img_url for user '{user['username']}' (ID: {user_id}).")
    return jsonify({'message': 'Profile updated successfully', 'img_url': img_url}), 200


if __name__ == '__main__':
    init_db()
    app.run(debug=True)
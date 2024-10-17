from http.server import BaseHTTPRequestHandler, HTTPServer
# import mysql.connector
import json
# import datetime
from UserService import Userservice1,create_tables

import jwt, datetime 
SECRET_KEY = 'f12s3curek3y'

class RequestHandler(BaseHTTPRequestHandler):
    
    def _send_response(self, status, response):
        self.send_response(status)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(response).encode('utf-8'))

    def _authenticate(self):
        auth_header = self.headers.get('Authorization')
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            try:
                decoded_token = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
                return decoded_token
            except jwt.ExpiredSignatureError:
                self._send_response(401, {"error": "Token has expired"})
            except jwt.InvalidTokenError:
                self._send_response(401, {"error": "Invalid token"})
        else:
            self._send_response(401, {"error": "Authorization header missing or invalid"})
        return None
    
    
    def do_POST(self):

        content_length = int(self.headers['Content-Length'])
        post_data = json.loads(self.rfile.read(content_length))

        # Handle user registration and login
        if self.path == "/register":
            response = Userservice1.register_user(
                post_data.get("username"),
                post_data.get("password"),
                post_data.get("role")
            )
            self._send_response(200 if "errors" not in response else 400, response)

        elif self.path == "/login":
            response = Userservice1.login_user(
                post_data.get("username"),
                post_data.get("password")
            )
            self._send_response(200 if "error" not in response else 401, response)

        # Handle ticket creation and assignment
        else:
            decoded_token = self._authenticate()
            if not decoded_token:
                return

            if self.path.startswith("/ticket/create"):
                response = Userservice1.create_ticket(
                    title=post_data.get("title"),
                    description=post_data.get("description"),
                    priority=post_data.get("priority"),
                    created_by=decoded_token['user_id']
                )
                self._send_response(200 if "errors" not in response else 400, response)

            elif self.path.startswith("/ticket/assign"):
                if decoded_token['role'] != 'admin':
                    self._send_response(403, {"error": "Forbidden"})
                    return
                response = Userservice1.assign_ticket(
                    ticket_id=post_data.get("ticket_id"),
                    assigned_to=post_data.get("assigned_to"),
                    requestor_role=decoded_token['role']
                )
                self._send_response(response[1], response[0])

            else:
                self._send_response(404, {"error": "Endpoint not found"})

   
    def do_GET(self):
        decoded_token = self._authenticate()
        if not decoded_token:
            return

        decoded_role = decoded_token.get('role')
        requestor_id = decoded_token.get('user_id')

        print(f"Requested Path: {self.path}")

        if self.path == "/users" and decoded_role == 'admin':
            response, status = Userservice1.get_user_profiles(requestor_role=decoded_role)

        elif self.path.startswith("/profile/"):
            try:
                user_id = int(self.path.split("/")[-1])
                response, status = Userservice1.get_user_profiles(user_id=user_id, requestor_role=decoded_role, requestor_id=requestor_id)
            except ValueError:
                response, status = {"error": "Invalid ID format"}, 400

        elif self.path == "/Tickets":
            if decoded_role != 'admin':
                self._send_response(403, {'error': 'Forbidden'})
                return
            response, status = Userservice1.get_all_tickets()

        elif self.path.startswith("/ticket/"):
            try:
                path_parts = self.path.split("/")
                if len(path_parts) == 3 and path_parts[2].isdigit():
                    user_id = int(path_parts[2])  # The ID from the URL path
                    response, status = Userservice1.get_ticket(requestor_id=requestor_id, decoded_role=decoded_role, user_id=user_id)
                else:
                    response, status = {'error': 'Invalid ID format'}, 400
            except ValueError:
                response, status = {'error': 'Invalid ID format'}, 400

        else:
            response, status = {'error': 'Endpoint not found'}, 404

        self._send_response(status, response)


    def do_PUT(self):
        content_length = int(self.headers['Content-Length'])
        put_data = json.loads(self.rfile.read(content_length))
        
        decoded_token = self._authenticate()
        if not decoded_token:
            return

        # Check the path and process accordingly
        if self.path.startswith("/profile/update/"):
            user_id = int(self.path.split("/")[-1])
            
            if decoded_token['user_id'] != user_id:
                self._send_response(403, {"error": "Forbidden: You can only update your own profile."})
                return
            
            response = Userservice1.update_user_profile(
                user_id=user_id,
                username=put_data.get("username"),
                password=put_data.get("password"),
                requestor_id=decoded_token['user_id']
            )
            self._send_response(200 if "errors" not in response else 400, response)

        elif self.path.startswith("/ticket/update"):
            ticket_id = put_data.get("ticket_id")
            response, status_code = Userservice1.update_ticket(
                ticket_id=ticket_id,
                title=put_data.get("title"),
                description=put_data.get("description"),
                priority=put_data.get("priority"),
                requestor_role=decoded_token['role'],
                requestor_id=decoded_token['user_id']
            )
            self._send_response(status_code, response)

        elif self.path.startswith("/ticket/status"):
            ticket_id = put_data.get("ticket_id")
            status = put_data.get("status")
            response, status_code = Userservice1.change_ticket_status(
                ticket_id=ticket_id,
                status=status,
                requestor_role=decoded_token['role'],
                requestor_id=decoded_token['user_id']
            )
            self._send_response(status_code, response)

        else:
            self._send_response(404, {"error": "Endpoint not found"})

# if __name__ == "__main__":
#    create_tables()
# run()

from http.server import BaseHTTPRequestHandler
import jwt,datetime
import mysql.connector
import json
SECRET_KEY = 'f12s3curek3y'

def create_connection():
     return mysql.connector.connect(
         host='localhost',
         user='root',
         password='root',
         database='train'
            )

def create_tables():
     connection = create_connection()
     cursor = connection.cursor()
     cursor.execute('''
     CREATE TABLE IF NOT EXISTS User (
     user_id INT AUTO_INCREMENT PRIMARY KEY,
     username VARCHAR(255) NOT NULL UNIQUE,
     password VARCHAR(255) NOT NULL,
     role ENUM('admin', 'user') NOT NULL
     );
    ''')
     cursor.execute('''
        CREATE TABLE IF NOT EXISTS Ticket (
            ticket_id INT AUTO_INCREMENT PRIMARY KEY,
            title VARCHAR(255) NOT NULL,
            description TEXT NOT NULL,
            priority ENUM('Low', 'Medium', 'High') NOT NULL,
            status ENUM('Open', 'In Progress', 'Resolved', 'Closed') DEFAULT 'Open',
            created_by INT NOT NULL,
            assigned_to INT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (created_by) REFERENCES User(user_id),
            FOREIGN KEY (assigned_to) REFERENCES User(user_id)
        );
    ''')
     cursor.close()
     connection.close()

class Userservice1(BaseHTTPRequestHandler):
    def register_user(username, password, role):
        errors = []
        
        if not isinstance(username, str) or not username.strip():
            errors.append("Please enter a valid username. It cannot be empty and must be a string.")
        
        if not isinstance(password, str) or not password.strip():
            errors.append("Please check your password. It cannot be empty and must be a string.")
        
        if not isinstance(role, str) or role not in ['admin', 'user']:
            errors.append("Error in role. You can add only 'admin' or 'user'.")

        connection = create_connection()
        cursor = connection.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM User WHERE username = %s", (username,))
        if cursor.fetchone()[0] > 0:
            errors.append("Username already exists. Please choose a different username.")
        
        if errors:
            return {"errors": errors}

        query = """
        INSERT INTO User (username, password, role)
        VALUES (%s, %s, %s)
        """
        values = (username, password, role)
        cursor.execute(query, values)
        connection.commit()
        cursor.close()
        connection.close()
        
        return {"message": f"User {username} registered successfully."}

    # Function to authenticate a user and generate a JWT token
    def login_user(username, password):
        connection = create_connection()
        cursor = connection.cursor(dictionary=True)
        
        cursor.execute("SELECT * FROM User WHERE username = %s AND password = %s", (username, password))
        user = cursor.fetchone()
        
        cursor.close()
        connection.close()
        
        if not user:
            return {"error": "Invalid username or password."}

        token = jwt.encode({
            'user_id': user['user_id'],
            'role': user['role'],
            'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=1)
        }, SECRET_KEY, algorithm='HS256')
        
        return {"token": token}

    def get_user_profiles(user_id=None, requestor_role=None, requestor_id=None):
        connection = create_connection()
        cursor = connection.cursor(dictionary=True)
        profiles = None 
        try:
            if requestor_role == 'admin' and user_id is None:
                query = "SELECT user_id, username, role FROM User"
                cursor.execute(query)
                profiles = cursor.fetchall()

            elif user_id:
                query = "SELECT user_id, username, role FROM User WHERE user_id = %s"
                cursor.execute(query, (user_id,))
                profiles = cursor.fetchone()

        finally:
            cursor.close()
            connection.close()

        if profiles:
            if requestor_role == 'admin' or (user_id == requestor_id):
                return profiles, 200
            else:
                return {"error": "Forbidden"}, 403
        else:
            return {"error": "User not found."}, 404



    def update_user_profile(user_id, username, password, requestor_id):
        errors = []

        # Validate inputs
        if not isinstance(username, str) or not username.strip():
            errors.append("Please enter a valid username. It cannot be empty and must be a string.")
        
        if not isinstance(password, str) or not password.strip():
            errors.append("Please check your password. It cannot be empty and must be a string.")
        
        if errors:
            return {"errors": errors}

        if user_id != requestor_id:
            return {"error": "Forbidden: You can only update your own profile."}, 403
        
        connection = create_connection()
        cursor = connection.cursor()
        
        query = "UPDATE User SET username = %s, password = %s WHERE user_id = %s"
        cursor.execute(query, (username, password, user_id))
        connection.commit()
        
        cursor.close()
        connection.close()
        
        return {"message": "User profile updated successfully."}

    def create_ticket(title, description, priority, created_by):
        errors = []
        
        if not isinstance(title, str) or not title.strip():
            errors.append("Title cannot be empty and must be a string.")
        
        if not isinstance(description, str) or not description.strip():
            errors.append("Description cannot be empty and must be a string.")
        
        if priority not in ['Low', 'Medium', 'High']:
            errors.append("Priority must be 'Low', 'Medium', or 'High'.")
        
        if errors:
            return {"errors": errors}

        connection = create_connection()
        cursor = connection.cursor()
        query = """
        INSERT INTO Ticket (title, description, priority, created_by)
        VALUES (%s, %s, %s, %s)
        """
        values = (title, description, priority, created_by)
        cursor.execute(query, values)
        connection.commit()
        cursor.close()
        connection.close()

        return {"message": "Ticket created successfully."}


    def get_ticket(requestor_id, decoded_role, user_id=None):
        try:
            connection = create_connection()
            cursor = connection.cursor(dictionary=True)

            if decoded_role == 'admin':
                if user_id is not None:
                    query = "SELECT * FROM Ticket WHERE created_by = %s"
                    cursor.execute(query, (user_id,))
                else:
                    query = "SELECT * FROM Ticket"
                    cursor.execute(query)
                tickets = cursor.fetchall()
                return {"message": "Here are the tickets", "tickets": tickets}, 200

            if decoded_role == 'user':
                query = "SELECT * FROM Ticket WHERE created_by = %s"
                cursor.execute(query, (requestor_id,))
                user_tickets = cursor.fetchall()

                if not user_tickets:
                    return {"message": "Please generate a ticket first"}, 404

                return {"tickets": user_tickets}, 200

        except mysql.connector.Error as err:
            print(f"Error: {err}")
            return {"error": "Database error"}, 500

        finally:
            cursor.close()
            connection.close()



    def get_all_tickets():
        

        connection = create_connection()
        cursor = connection.cursor(dictionary=True)

        query = "SELECT * FROM Ticket"
        cursor.execute(query)
        tickets = cursor.fetchall()

        cursor.close()
        connection.close()

        return tickets, 200

    def update_ticket(ticket_id, title, description, priority, requestor_role, requestor_id):
        errors = []
        
        if title and (not isinstance(title, str) or not title.strip()):
            errors.append("Title cannot be empty and must be a string.")
        
        if description and (not isinstance(description, str) or not description.strip()):
            errors.append("Description cannot be empty and must be a string.")
        
        if priority and priority not in ['Low', 'Medium', 'High']:
            errors.append("Priority must be 'Low', 'Medium', or 'High'.")
        
        if errors:
            return {"errors": errors}

        connection = create_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute("SELECT * FROM Ticket WHERE ticket_id = %s", (ticket_id,))
        ticket = cursor.fetchone()
        
        if not ticket:
            cursor.close()
            connection.close()
            return {"error": "Ticket not found."}, 404

        if requestor_role != 'admin' and requestor_role != 'user' and ticket.get('created_by') != requestor_id:
         return {"error": "Unauthorized to update this ticket."}, 403

        query = "UPDATE Ticket SET title = %s, description = %s, priority = %s WHERE ticket_id = %s"
        values = (
            title or ticket['title'], 
            description or ticket['description'], 
            priority or ticket['priority'],
            ticket_id
        )
        
        cursor.execute(query, values)
        connection.commit()

        cursor.close()
        connection.close()

        return {"message": "Ticket updated successfully."}, 200

    def assign_ticket(ticket_id, assigned_to, requestor_role):
        if requestor_role != 'admin':
            return {"error": "Forbidden"}, 403

        connection = create_connection()
        cursor = connection.cursor()

        cursor.execute("SELECT * FROM Ticket WHERE ticket_id = %s", (ticket_id,))
        ticket = cursor.fetchone()
        
        if not ticket:
            return {"error": "Ticket not found."}, 404

        cursor.execute("SELECT COUNT(*) FROM User WHERE user_id = %s", (assigned_to,))
        if cursor.fetchone()[0] == 0:
            return {"error": "Assigned user not found."}, 404

        query = "UPDATE Ticket SET assigned_to = %s WHERE ticket_id = %s"
        cursor.execute(query, (assigned_to, ticket_id))
        connection.commit()

        cursor.close()
        connection.close()

        return {"message": "Ticket assigned successfully."}, 200

 
     def change_ticket_status(ticket_id, status, requestor_role, requestor_id):
        if status not in ['Open', 'In Progress', 'Resolved', 'Closed']:
            return {"error": "Invalid status value."}, 400

        connection = create_connection()
        cursor = connection.cursor(dictionary=True)  # Ensure dictionary=True to get named columns
        print(f"Changing status for ticket_id: {ticket_id}")

        cursor.execute("SELECT * FROM Ticket WHERE ticket_id = %s", (ticket_id,))
        ticket = cursor.fetchone()

        # Debugging information
        print("Fetched ticket:", ticket)

        if not ticket:
            return {"error": "Ticket not found."}, 404

        if requestor_role != 'admin' and ticket.get('created_by') != requestor_id:
            return {"error": "Forbidden"}, 403

        query = "UPDATE Ticket SET status = %s WHERE ticket_id = %s"
        cursor.execute(query, (status, ticket_id))
        connection.commit()

        cursor.close()
        connection.close()

        return {"message": "Ticket status updated successfully."}, 200

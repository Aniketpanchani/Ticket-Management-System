from controller import RequestHandler,create_tables
from http.server import HTTPServer


def run(server_class=HTTPServer, handler_class=RequestHandler, port=8000):
     server_address = ('', port)
     httpd = server_class(server_address, handler_class)
     print(f"Starting server on port {port}...")
     httpd.serve_forever()

if __name__ == "__main__":
   create_tables()
run()
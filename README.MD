sudo systemctl daemon-reload
Step 4: Enable and Start the Service
Enable the service to start it automatically on boot:

bash
Copy code
sudo systemctl enable your_service_name
Start the service:

bash
Copy code
sudo systemctl start your_service_name
Verify the service status:

bash
Copy code
sudo systemctl status your_service_name
This will show the status of your service, including logs if there are any errors.
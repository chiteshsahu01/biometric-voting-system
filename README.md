\# Biometric Voting System



A minor project developed as part of the MCA curriculum.



\## Project Overview



The Biometric Voting System is a web-based application designed to demonstrate voter registration, face verification, and voting workflows.



\## Technology Stack



\- \*\*Backend:\*\* Python, Flask

\- \*\*Database:\*\* MySQL

\- \*\*Face Verification:\*\* OpenCV, DeepFace

\- \*\*Frontend:\*\* HTML, CSS, JavaScript



\## Features



\- User authentication

\- Face registration and verification

\- Database-backed voter management

\- Voting workflow



\## Requirements



\- Python 3.12

\- MySQL Server

\- Required Python packages listed in `requirements.txt`



\## Local Setup



1\. Clone or download this repository.

2\. Create and activate a Python virtual environment.

3\. Install the dependencies:



&#x20;  ```bash

&#x20;  pip install -r requirements.txt

&#x20;  ```



4\. Create a local `.env` file with your database configuration:



&#x20;  ```env

&#x20;  DB\_HOST=localhost

&#x20;  DB\_PORT=3306

&#x20;  DB\_USER=your\_mysql\_username

&#x20;  DB\_PASSWORD=your\_mysql\_password

&#x20;  DB\_NAME=biometric\_voting

&#x20;  ```



5\. Ensure the MySQL database and required tables are set up.

6\. Start the application:



&#x20;  ```bash

&#x20;  python run.py

&#x20;  ```



7\. Open the local address shown in the terminal.



\## Important Notes



\- Never commit `.env`, database backups, voter records, or biometric images.

\- This project is for academic demonstration and testing, not a certified election system.

\- Database schema/setup instructions may need to be added separately.



\## License



No license has been specified yet.




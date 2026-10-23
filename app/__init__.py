import os

from datetime import datetime

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session,
    jsonify
)

from config import DB_CONFIG

from werkzeug.security import (
    check_password_hash,
    generate_password_hash
)

from app.models import (
    db,
    Admin,
    Voter,
    Election,
    Candidate,
    FaceVerification,
    Vote
)

from app.services.face_service import (
    save_face_image,
    verify_face,
    create_temporary_face_path,
    find_duplicate_face
)



def update_election_statuses():

    now = datetime.now()

    elections = Election.query.all()

    changed = False

    # First, complete elections whose end time has passed
    for election in elections:

        if election.status == "COMPLETED":
            continue

        if now >= election.end_date:
            election.status = "COMPLETED"
            changed = True

    # Check whether an active election already exists
    active_election = Election.query.filter_by(
        status="ACTIVE"
    ).first()

    # If no election is active, activate only the earliest
    # eligible upcoming election
    if not active_election:

        upcoming_election = Election.query.filter(
            Election.status == "UPCOMING",
            Election.start_date <= now,
            Election.end_date > now
        ).order_by(
            Election.start_date.asc()
        ).first()

        if upcoming_election:
            upcoming_election.status = "ACTIVE"
            changed = True

    if changed:
        db.session.commit()

def create_app():

    app = Flask(__name__)

    # MySQL Database Configuration
    app.config["SQLALCHEMY_DATABASE_URI"] = (
        f"mysql+pymysql://"
        f"{DB_CONFIG['user']}:{DB_CONFIG['password']}"
        f"@{DB_CONFIG['host']}:{DB_CONFIG['port']}"
        f"/{DB_CONFIG['database']}"
    )

    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # Secret key for session and flash messages
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")

    # Initialize Database
    db.init_app(app)

    @app.route("/")
    def home():
        return render_template("index.html")


    @app.route("/voter-login", methods=["GET", "POST"])
    def voter_login():

        if request.method == "POST":

            voter_username = request.form.get("voter_id")
            password = request.form.get("password")

            if not voter_username or not password:
                flash("Invalid Voter ID or Password.")
                return redirect(url_for("voter_login"))

            voter = Voter.query.filter_by(
                username=voter_username
            ).first()

            if not voter or not voter.password_hash:
                flash("Invalid Voter ID or Password.")
                return redirect(url_for("voter_login"))

            if not check_password_hash(
                voter.password_hash,
                password
            ):
                flash("Invalid Voter ID or Password.")
                return redirect(url_for("voter_login"))

            if voter.status == "BLOCKED":
                flash("Your voter account is blocked.")
                return redirect(url_for("voter_login"))

            verification = FaceVerification.query.filter_by(
                voter_id=voter.voter_id
            ).first()

            if voter.status == "PENDING":

                if verification and verification.verification_status == "VERIFIED":
                    voter.status = "VERIFIED"
                    db.session.commit()

                elif verification and verification.verification_status == "REGISTERED":
                    return redirect(url_for("face_verification"))

                else:
                    return redirect(url_for("face_registration"))

            if voter.status != "VERIFIED":
                flash("Your voter account is not verified yet.")
                return redirect(url_for("voter_login"))

            # Login successful
            session["user_id"] = voter.voter_id
            session["voter_id"] = voter.voter_id
            session["voter_name"] = voter.full_name
            session["role"] = "VOTER"

            return redirect(url_for("voter_dashboard"))

        return render_template("voter_login.html")


    @app.route("/voter-dashboard")
    def voter_dashboard():

        if "user_id" not in session:
            return redirect(url_for("voter_login"))

        update_election_statuses()

        active_election = Election.query.filter_by(
            status="ACTIVE"
        ).first()

        candidates = []

        if active_election:
            candidates = Candidate.query.filter_by(
                election_id=active_election.election_id
            ).all()

        return render_template(
            "voter_dashboard.html",
            election=active_election,
            candidates=candidates
        )

    @app.route("/voter-profile")
    def voter_profile():

        if "user_id" not in session:
            return redirect(url_for("voter_login"))

        voter = Voter.query.get(session["voter_id"])

        if not voter:
            flash("Voter profile not found.")
            return redirect(url_for("voter_dashboard"))

        verification = FaceVerification.query.filter_by(
            voter_id=voter.voter_id
        ).first()

        return render_template(
            "voter_profile.html",
            voter=voter,
            verification=verification
        )

    @app.route("/face-verification")
    def face_verification():

        if "user_id" not in session:
            return redirect(url_for("voter_login"))

        voter_id = session.get("voter_id")

        if not voter_id:
            flash("Please login as a voter first.")
            return redirect(url_for("voter_login"))

        verification = FaceVerification.query.filter_by(
            voter_id=voter_id
        ).first()

        return render_template(
            "face_verification.html",
            verification=verification
        )

    @app.route("/voter-logout")
    def voter_logout():

        session.clear()

        return redirect(url_for("voter_login"))

    
    @app.route("/admin-login", methods=["GET", "POST"])
    def admin_login():

        if request.method == "POST":

            username = request.form.get("username")
            password = request.form.get("password")

            if not username or not password:
                flash("Please enter username and password.")
                return render_template("admin_login.html")

            admin = Admin.query.filter_by(
                username=username
            ).first()

            if not admin:
                flash("Invalid admin credentials.")
                return render_template("admin_login.html")

            if not check_password_hash(
                admin.password_hash,
                password
            ):
                flash("Invalid admin credentials.")
                return render_template("admin_login.html")

            session.clear()

            session["user_id"] = admin.admin_id
            session["username"] = admin.username
            session["role"] = "ADMIN"

            return redirect(url_for("admin_dashboard"))

        return render_template("admin_login.html")

    @app.route("/admin/elections", methods=["GET", "POST"])
    def admin_elections():

        if "user_id" not in session:
            return redirect(url_for("admin_login"))

        if session.get("role") != "ADMIN":
            return redirect(url_for("home"))

        update_election_statuses()

        if request.method == "POST":

            election_name = request.form.get("election_name")
            description = request.form.get("description")
            start_date = request.form.get("start_date")
            start_time = request.form.get("start_time")

            end_date = request.form.get("end_date")
            end_time = request.form.get("end_time")

            if not election_name or not start_date or not start_time or not end_date or not end_time:
                flash("Please fill all required fields.")
                return redirect(url_for("admin_elections"))

            try:

                start_datetime = datetime.strptime(
                    f"{start_date} {start_time}",
                    "%Y-%m-%d %H:%M"
                )

                end_datetime = datetime.strptime(
                    f"{end_date} {end_time}",
                    "%Y-%m-%d %H:%M"
                )

                if end_datetime <= start_datetime:
                    flash("End date must be after start date.")
                    return redirect(url_for("admin_elections"))

                election = Election(
                    election_name=election_name,
                    description=description,
                    start_date=start_datetime,
                    end_date=end_datetime,
                    status="UPCOMING"
                )

                db.session.add(election)
                db.session.commit()

                flash("Election created successfully!")

                return redirect(url_for("admin_elections"))

            except ValueError:

                flash("Invalid date and time format.")
                return redirect(url_for("admin_elections"))

            except Exception as error:

                db.session.rollback()

                flash(f"Error creating election: {error}")

                return redirect(url_for("admin_elections"))

        elections = Election.query.order_by(
            Election.created_at.desc()
        ).all()

        return render_template(
            "admin_elections.html",
            elections=elections
        )

    @app.route("/admin/elections/<int:election_id>/status", methods=["POST"])
    def update_election_status(election_id):

        if "user_id" not in session:
            return redirect(url_for("admin_login"))

        if session.get("role") != "ADMIN":
            return redirect(url_for("home"))

        election = Election.query.get(election_id)

        if not election:
            flash("Election not found.")
            return redirect(url_for("admin_elections"))

        new_status = request.form.get("status")

        allowed_statuses = ["UPCOMING", "ACTIVE", "COMPLETED"]

        if new_status not in allowed_statuses:
            flash("Invalid election status.")
            return redirect(url_for("admin_elections"))

        # Only one election can be ACTIVE at a time
        if new_status == "ACTIVE":

            active_election = Election.query.filter(
                Election.status == "ACTIVE",
                Election.election_id != election.election_id
            ).first()

            if active_election:
                flash(
                    f"Another election is already active: "
                    f"{active_election.election_name}"
                )
                return redirect(url_for("admin_elections"))

        election.status = new_status

        db.session.commit()

        flash("Election status updated successfully!")

        return redirect(url_for("admin_elections"))

    @app.route("/admin/elections/<int:election_id>/edit", methods=["GET", "POST"])
    def edit_election(election_id):
        if "user_id" not in session:
            return redirect(url_for("admin_login"))

        if session.get("role") != "ADMIN":
            return redirect(url_for("home"))

        election = Election.query.get(election_id)

        if not election:
            flash("Election not found.")
            return redirect(url_for("admin_elections"))

        if request.method == "POST":
            election_name = request.form.get("election_name")
            description = request.form.get("description")
            start_date = request.form.get("start_date")
            end_date = request.form.get("end_date")

            if not election_name or not start_date or not end_date:
                flash("Please fill all required fields.")
                return redirect(
                    url_for("edit_election", election_id=election_id)
                )

            try:
                start_datetime = datetime.strptime(
                    start_date, "%Y-%m-%dT%H:%M"
                )

                end_datetime = datetime.strptime(
                    end_date, "%Y-%m-%dT%H:%M"
                )

                if end_datetime <= start_datetime:
                    flash("End date must be after start date.")
                    return redirect(
                        url_for("edit_election", election_id=election_id)
                    )

                election.election_name = election_name
                election.description = description
                election.start_date = start_datetime
                election.end_date = end_datetime

                db.session.commit()

                flash("Election updated successfully!")
                return redirect(url_for("admin_elections"))

            except ValueError:
                flash("Invalid date and time format.")
                return redirect(
                    url_for("edit_election", election_id=election_id)
                )

            except Exception as error:
                db.session.rollback()
                flash(f"Error updating election: {error}")
                return redirect(
                    url_for("edit_election", election_id=election_id)
                )

        return render_template(
            "edit_election.html",
            election=election
        )

    @app.route("/admin/elections/<int:election_id>/delete", methods=["POST"])
    def delete_election(election_id):
        if "user_id" not in session:
            return redirect(url_for("admin_login"))

        if session.get("role") != "ADMIN":
            return redirect(url_for("home"))

        election = Election.query.get(election_id)

        if not election:
            flash("Election not found.")
            return redirect(url_for("admin_elections"))

        # Do not delete an election that already has votes
        vote_count = Vote.query.filter_by(
            election_id=election.election_id
        ).count()

        if vote_count > 0:
            flash("Election cannot be deleted because votes already exist.")
            return redirect(url_for("admin_elections"))

        try:
            # Delete candidates belonging to this election first
            Candidate.query.filter_by(
                election_id=election.election_id
            ).delete()

            db.session.delete(election)
            db.session.commit()

            flash("Election deleted successfully!")

        except Exception as error:
            db.session.rollback()
            flash(f"Error deleting election: {error}")

        return redirect(url_for("admin_elections"))

    @app.route("/admin/candidates", methods=["GET", "POST"])
    def admin_candidates():

        if "user_id" not in session:
            return redirect(url_for("admin_login"))

        if session.get("role") != "ADMIN":
            return redirect(url_for("home"))

        if request.method == "POST":

            election_id = request.form.get("election_id")
            candidate_name = request.form.get("candidate_name")
            party_name = request.form.get("party_name")
            symbol = request.form.get("symbol")
            description = request.form.get("description")

            if not election_id or not candidate_name:
                flash("Election and candidate name are required.")
                return redirect(url_for("admin_candidates"))

            try:

                election = Election.query.get(int(election_id))

                if not election:
                    flash("Election not found.")
                    return redirect(url_for("admin_candidates"))

                candidate = Candidate(
                    election_id=election.election_id,
                    candidate_name=candidate_name,
                    party_name=party_name,
                    symbol=symbol,
                    description=description
                )

                db.session.add(candidate)
                db.session.commit()

                flash("Candidate added successfully!")

                return redirect(url_for("admin_candidates"))

            except Exception as error:

                db.session.rollback()

                flash(f"Error adding candidate: {error}")

                return redirect(url_for("admin_candidates"))

        elections = Election.query.order_by(
            Election.created_at.desc()
        ).all()

        candidates = Candidate.query.order_by(
            Candidate.created_at.desc()
        ).all()

        return render_template(
            "admin_candidates.html",
            elections=elections,
            candidates=candidates
        )

    @app.route("/admin/candidates/<int:candidate_id>/edit", methods=["GET", "POST"])
    def edit_candidate(candidate_id):
        if "user_id" not in session:
            return redirect(url_for("admin_login"))

        if session.get("role") != "ADMIN":
            return redirect(url_for("home"))

        candidate = Candidate.query.get(candidate_id)

        if not candidate:
            flash("Candidate not found.")
            return redirect(url_for("admin_candidates"))

        elections = Election.query.order_by(Election.created_at.desc()).all()

        if request.method == "POST":
            election_id = request.form.get("election_id")
            candidate_name = request.form.get("candidate_name")
            party_name = request.form.get("party_name")
            symbol = request.form.get("symbol")
            description = request.form.get("description")

            if not election_id or not candidate_name:
                flash("Election and candidate name are required.")
                return redirect(url_for("edit_candidate", candidate_id=candidate_id))

            election = Election.query.get(int(election_id))

            if not election:
                flash("Election not found.")
                return redirect(url_for("edit_candidate", candidate_id=candidate_id))

            candidate.election_id = election.election_id
            candidate.candidate_name = candidate_name
            candidate.party_name = party_name
            candidate.symbol = symbol
            candidate.description = description

            try:
                db.session.commit()
                flash("Candidate updated successfully!")
                return redirect(url_for("admin_candidates"))
            except Exception as error:
                db.session.rollback()
                flash(f"Error updating candidate: {error}")
                return redirect(url_for("edit_candidate", candidate_id=candidate_id))

        return render_template(
            "edit_candidate.html",
            candidate=candidate,
            elections=elections
        )

    @app.route("/admin/candidates/<int:candidate_id>/delete", methods=["POST"])
    def delete_candidate(candidate_id):
        if "user_id" not in session:
            return redirect(url_for("admin_login"))

        if session.get("role") != "ADMIN":
            return redirect(url_for("home"))

        candidate = Candidate.query.get(candidate_id)

        if not candidate:
            flash("Candidate not found.")
            return redirect(url_for("admin_candidates"))

        try:
            db.session.delete(candidate)
            db.session.commit()
            flash("Candidate deleted successfully!")
        except Exception as error:
            db.session.rollback()
            flash(f"Error deleting candidate: {error}")

        return redirect(url_for("admin_candidates"))

    @app.route("/admin-dashboard")
    def admin_dashboard():

        if "user_id" not in session:
            return redirect(url_for("admin_login"))

        if session.get("role") != "ADMIN":
            return redirect(url_for("home"))

        return render_template(
            "admin_dashboard.html"
        )

    @app.route("/admin/results")
    def admin_results():

        if "user_id" not in session:
            return redirect(url_for("admin_login"))

        if session.get("role") != "ADMIN":
            return redirect(url_for("home"))

        elections = Election.query.order_by(
            Election.created_at.desc()
        ).all()

        selected_election_id = request.args.get("election_id")

        if selected_election_id:
            election = Election.query.get(
                int(selected_election_id)
            )
        else:
            election = Election.query.filter_by(
                status="ACTIVE"
            ).first()

            if not election and elections:
                election = elections[0]

        results = []
        total_votes = 0

        if election:

            candidates = Candidate.query.filter_by(
                election_id=election.election_id
            ).all()

            for candidate in candidates:

                vote_count = Vote.query.filter_by(
                    election_id=election.election_id,
                    candidate_id=candidate.candidate_id
                ).count()

                results.append({
                    "candidate": candidate,
                    "vote_count": vote_count
                })

                total_votes += vote_count

            for item in results:

                if total_votes > 0:
                    item["percentage"] = round(
                        (item["vote_count"] / total_votes) * 100,
                        2
                    )
                else:
                    item["percentage"] = 0

        winner = None

        if results and total_votes > 0:

            winner = max(
                results,
                key=lambda item: item["vote_count"]
            )

        return render_template(
            "admin_results.html",
            elections=elections,
            election=election,
            results=results,
            total_votes=total_votes,
            winner=winner
        )

    @app.route("/admin/voters")
    def admin_voters():

        if "user_id" not in session:
            return redirect(url_for("admin_login"))

        if session.get("role") != "ADMIN":
            return redirect(url_for("home"))

        voters = Voter.query.order_by(
            Voter.created_at.desc()
        ).all()

        return render_template(
            "admin_voters.html",
            voters=voters
        )

    @app.route("/admin/voters/<int:voter_id>/toggle-status", methods=["POST"])
    def toggle_voter_status(voter_id):
        if "user_id" not in session:
            return redirect(url_for("admin_login"))

        if session.get("role") != "ADMIN":
            return redirect(url_for("home"))

        voter = Voter.query.get(voter_id)

        if not voter:
            flash("Voter not found.")
            return redirect(url_for("admin_voters"))

        if voter.status == "BLOCKED":
            voter.status = "VERIFIED"
            flash("Voter unblocked successfully.")
        else:
            voter.status = "BLOCKED"
            flash("Voter blocked successfully.")

        db.session.commit()

        return redirect(url_for("admin_voters"))


    @app.route("/face-registration", methods=["GET", "POST"])
    def face_registration():

        if "user_id" not in session:
            return redirect(url_for("voter_login"))

        voter_id = session["voter_id"]

        voter = Voter.query.get(voter_id)

        if not voter:
            flash("Voter profile not found.")
            return redirect(url_for("voter_dashboard"))

        if request.method == "POST":

            image_data = request.form.get("image")

            if not image_data:
                return jsonify({
                    "success": False,
                    "message": "No face image received."
                }), 400

            captured_path = None
            
            try:
                captured_path = create_temporary_face_path(
                    voter.voter_number
                )

                save_face_image(
                    voter.voter_number,
                    image_data,
                    filename=os.path.basename(captured_path)
                )

                duplicate_voter = find_duplicate_face(
                    captured_path,
                    exclude_voter_number=voter.voter_number
                )

                if duplicate_voter:
                    return jsonify({
                        "success": False,
                        "message": (
                            "This face may already be registered "
                            "with another voter. Registration blocked."
                        )
                    }), 409

                # Save permanently only after duplicate check passes
                save_face_image(
                    voter.voter_number,
                    image_data
                )

                verification = FaceVerification.query.filter_by(
                    voter_id=voter.voter_id
                ).first()

                if verification:
                    verification.verification_status = "REGISTERED"
                    verification.verification_method = "FACE"
                else:
                    verification = FaceVerification(
                        voter_id=voter.voter_id,
                        verification_status="REGISTERED",
                        verification_method="FACE"
                    )
                    db.session.add(verification)

                db.session.commit()

                return jsonify({
                    "success": True,
                    "message": "Face registered successfully."
                })

            except Exception as error:
                db.session.rollback()

                return jsonify({
                    "success": False,
                    "message": (
                        "Face registration could not be completed. "
                        "Please try again with a clear face image."
                    )
                }), 500

            finally:
                if (
                    captured_path
                    and os.path.exists(captured_path)
                ):
                    try:
                        os.remove(captured_path)
                    except OSError:
                        pass

        return render_template(
            "face_registration.html",
            voter=voter
        )

    @app.route("/voter-register", methods=["GET", "POST"])
    def voter_register():

        if request.method == "POST":

            voter_number = request.form.get("voter_number")
            full_name = request.form.get("full_name")
            date_of_birth = request.form.get("date_of_birth")

            # Validate date of birth
            if date_of_birth:
                try:
                    dob = datetime.strptime(date_of_birth, "%Y-%m-%d").date()

                    if dob > datetime.now().date():
                        flash("Date of birth cannot be in the future.")
                        return redirect(url_for("voter_register"))

                except ValueError:
                    flash("Invalid date of birth.")
                    return redirect(url_for("voter_register"))

            gender = request.form.get("gender")
            mobile = request.form.get("mobile")
            address = request.form.get("address")
            username = request.form.get("username")
            password = request.form.get("password")

            # Validate mobile number
            if mobile and (not mobile.isdigit() or len(mobile) != 10):
                flash("Please enter a valid 10-digit mobile number.")
                return redirect(url_for("voter_register"))

            # Validate password
            if len(password) < 6:
                flash("Password must be at least 6 characters long.")
                return redirect(url_for("voter_register"))

            # Validate required fields
            if not all([
                voter_number and voter_number.strip(),
                full_name and full_name.strip(),
                username and username.strip(),
                password and password.strip()
            ]):
                flash("Please fill all required fields.")
                return redirect(url_for("voter_register"))
            
            try:

                # Check duplicate username in voters
                existing_voter_username = Voter.query.filter_by(
                    username=username
                ).first()

                if existing_voter_username:
                    flash("Username already exists.")
                    return redirect(url_for("voter_register"))

                # Check duplicate voter number
                existing_voter = Voter.query.filter_by(
                    voter_number=voter_number
                ).first()

                if existing_voter:
                    flash("Voter number already exists.")
                    return redirect(url_for("voter_register"))
                
                # Create voter profile
                voter = Voter(
                    username=username,
                    password_hash=generate_password_hash(password),
                    voter_number=voter_number,
                    full_name=full_name,
                    date_of_birth=(
                        datetime.strptime(
                            date_of_birth,
                            "%Y-%m-%d"
                        ).date()
                        if date_of_birth
                        else None
                    ),
                    gender=gender,
                    mobile=mobile,
                    address=address,
                    status="PENDING"
                )

                db.session.add(voter)
                db.session.commit()

                # Create face verification record
                verification = FaceVerification(
                    voter_id=voter.voter_id,
                    verification_status="NOT_REGISTERED",
                    verification_method="FACE"
                )

                db.session.add(verification)
                db.session.commit()

                # Login newly registered voter
                session.clear()
                session["user_id"] = voter.voter_id
                session["voter_id"] = voter.voter_id
                session["voter_name"] = voter.full_name

                return redirect(url_for("face_registration"))

            except ValueError:
                db.session.rollback()
                flash("Invalid date of birth.")
                return redirect(url_for("voter_register"))

            except Exception as error:
                db.session.rollback()
                flash(f"Registration error: {error}")
                return redirect(url_for("voter_register"))

        return render_template("voter_register.html")


    @app.route("/face-verification/check", methods=["POST"])
    def face_verification_check():

        if "user_id" not in session:
            return jsonify({
                "success": False,
                "message": "Please login first."
            }), 401

        voter_id = session.get("voter_id")

        if not voter_id:
            return jsonify({
                "success": False,
                "message": "Please login as a voter first."
            }), 401

        voter = Voter.query.get(voter_id)

        if not voter:
            return jsonify({
                "success": False,
                "message": "Voter profile not found."
            }), 404

        image_data = request.form.get("image")

        if not image_data:
            return jsonify({
                "success": False,
                "message": "No face image received."
            }), 400

        captured_path = None

        try:

            # Create unique temporary file
            captured_path = create_temporary_face_path(
                voter.voter_number
            )

            # Save captured image
            save_face_image(
                voter.voter_number,
                image_data,
                filename=os.path.basename(captured_path)
            )

            # Check whether this face belongs to another registered voter
            duplicate_voter = find_duplicate_face(
                captured_path,
                exclude_voter_number=voter.voter_number
            )

            if duplicate_voter:
                return jsonify({
                    "success": True,
                    "verified": False,
                    "message": "This face is already registered with another voter."
                }), 409

            # Verify against registered face
            result = verify_face(
                voter.voter_number,
                captured_path
            )

            verification = FaceVerification.query.filter_by(
                voter_id=voter.voter_id
            ).first()

            if result["verified"]:

                if verification:
                    verification.verification_status = "VERIFIED"
                else:
                    verification = FaceVerification(
                        voter_id=voter.voter_id,
                        verification_status="VERIFIED",
                        verification_method="FACE"
                    )
                    db.session.add(verification)

                voter.status = "VERIFIED"
                db.session.commit()

                return jsonify({
                    "success": True,
                    "verified": True,
                    "message": "Face verification successful.",
                    "confidence": result["confidence"]
                })

            else:

                if verification:
                    verification.verification_status = "FAILED"
                    db.session.commit()

                return jsonify({
                    "success": True,
                    "verified": False,
                    "message": "Face verification failed."
                })

        except Exception as error:

            db.session.rollback()

            return jsonify({
                "success": False,
                "message": f"Verification error: {error}"
            }), 500

        finally:

            # Delete temporary image
            if captured_path and os.path.exists(captured_path):

                try:
                    os.remove(captured_path)
                except OSError:
                    pass

    @app.route("/cast-vote")
    def cast_vote():

        if "user_id" not in session:
            return redirect(url_for("voter_login"))

        voter = Voter.query.get(session["voter_id"])

        if not voter:
            flash("Voter profile not found.")
            return redirect(url_for("voter_dashboard"))

        if voter.status == "BLOCKED":
            flash("Your voter account is blocked.")
            return redirect(url_for("voter_dashboard"))

        # Face verification required
        verification = FaceVerification.query.filter_by(
            voter_id=voter.voter_id
        ).first()

        if not verification or verification.verification_status != "VERIFIED":
            flash("Please complete face verification first.")
            return redirect(url_for("face_verification"))

        # Automatically update election statuses
        update_election_statuses()

        # Get active election
        election = Election.query.filter_by(
            status="ACTIVE"
        ).first()

        if not election:
            flash("There is currently no active election.")
            return redirect(url_for("voter_dashboard"))

        # Check whether voter has already voted
        existing_vote = Vote.query.filter_by(
            voter_id=voter.voter_id,
            election_id=election.election_id
        ).first()

        if existing_vote:
            flash("You have already voted in this election.")
            return redirect(url_for("voter_dashboard"))

        candidates = Candidate.query.filter_by(
            election_id=election.election_id
        ).all()

        return render_template(
            "cast_vote.html",
            voter=voter,
            election=election,
            candidates=candidates
        )

    @app.route("/submit-vote", methods=["POST"])
    def submit_vote():

        if "user_id" not in session:
            return redirect(url_for("voter_login"))

        voter = Voter.query.get(session["voter_id"])

        if not voter:
            flash("Voter profile not found.")
            return redirect(url_for("voter_dashboard"))

        # Face verification required
        verification = FaceVerification.query.filter_by(
            voter_id=voter.voter_id
        ).first()

        if not verification or verification.verification_status != "VERIFIED":
            flash("Please complete face verification first.")
            return redirect(url_for("face_verification"))

        # Get active election
        election = Election.query.filter_by(
            status="ACTIVE"
        ).first()

        if not election:
            flash("There is currently no active election.")
            return redirect(url_for("voter_dashboard"))

        # Get selected candidate
        candidate_id = request.form.get("candidate_id")

        if not candidate_id:
            flash("Please select a candidate.")
            return redirect(url_for("cast_vote"))

        candidate = Candidate.query.filter_by(
            candidate_id=candidate_id,
            election_id=election.election_id
        ).first()

        if not candidate:
            flash("Invalid candidate selected.")
            return redirect(url_for("cast_vote"))

        # Prevent duplicate voting
        existing_vote = Vote.query.filter_by(
            voter_id=voter.voter_id,
            election_id=election.election_id
        ).first()

        if existing_vote:
            flash("You have already voted in this election.")
            return redirect(url_for("voter_dashboard"))

        # Save vote
        vote = Vote(
            voter_id=voter.voter_id,
            election_id=election.election_id,
            candidate_id=candidate.candidate_id
        )

        db.session.add(vote)
        db.session.commit()

        return render_template(
            "vote_success.html",
            voter=voter,
            election=election,
            candidate=candidate
        )

    return app
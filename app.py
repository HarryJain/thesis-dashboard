from flask import Flask, render_template
app = Flask(__name__)
app.config["TEMPLATES_AUTO_RELOAD"] = True

@app.route("/")
def home():
    return render_template("home.html")

@app.route("/about/")
def about():
    return render_template("construction.html")

@app.route("/proposal/")
def proposal():
    #return render_template("proposal.html")
    return app.send_static_file("CPSC_490_Project_Proposal_Final_Advisor.pdf")

@app.route("/teams/")
def teams():
    return render_template("construction.html")

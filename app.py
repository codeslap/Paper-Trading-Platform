import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime
import numbers

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    if request.method == "GET":
        # make sure session is valid
        id = session["user_id"]
        hi = db.execute("SELECT * FROM users where id = ?", id)
        #if user not in db, redirect to registration
        if not hi:
            redirect ("/register.html")
        # setting up variables for for loop below
        info = db.execute("SELECT * FROM history WHERE user = ? and time is NULL and total > 0", id)
        leni = len(info)
        stockinfo = []
        money = db.execute("SELECT cash FROM users WHERE id = ?", id)
        try:
            amount = float(money[0]["cash"])
        except IndexError:
            return apology("something has gone wrong")
        # keeps track of total cash value + stocks value
        stocktotal = 0
        for i in range(0,leni):
            stockinfo.append(lookup(info[i]["stock"]))
            symbol = stockinfo[i]["symbol"]
            total = int(info[i]["total"])
            currprice = float(stockinfo[i]["price"])
            stocktotal +=  (total*currprice)
            #updates price and value in database before showing portfolio
            db.execute("UPDATE history SET value = ?, price = ? WHERE stock = ? and user = ? and time is NULL", currprice*total, currprice, symbol.lower(), id)
        stocktotal = amount + stocktotal
        #calling database again to send updates values to index.html
        info = db.execute("SELECT * FROM history WHERE user = ? and time is NULL and total > 0", id)
        return render_template("index.html", info=info, leni = leni, stockinfo=stockinfo, amount=amount, stocktotal = stocktotal)



@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "POST":
       #validate entries
       if not request.form.get("symbol"):
            return apology("Please insert a stock symbol")
       if not request.form.get("shares"):
            return apology("Please insert shares")
       stock = lookup(request.form.get("symbol"))
       if not stock:
            return apology("Please insert a valid stock ticker")
       shares = request.form.get("shares")
       try:
           shares = float(shares)
       except ValueError:
            return apology("Please insert valid shares")
       shares = float(shares)
       intshares = int(shares)
       if intshares != shares:
            return apology("please insert valid shares")
       if shares < 1:
            return apology("Please insert valid number of shares")
       # setting up variables to make sure user has enough money
       id = session["user_id"]
       money = db.execute("SELECT cash FROM users WHERE id = ?", id)
       amount = money[0]["cash"]
       price = float(stock["price"])
       # checks if user has enough for purchase
       if amount < price*shares:
            return apology("Not enough money")
       # once everything is validated, begin updating database
       else:
            time = datetime.now()
            # inserts purchase order information into database
            db.execute("INSERT INTO history (user, bought, stock, time, price) VALUES(?,?,?,?,?)", id, int(shares), request.form.get("symbol").lower(), time, price)
            # checking if total stock count exists or if first time buying that specific stock
            totalq = db.execute("SELECT total FROM history WHERE user = ? and stock = ? and time is NULL", id, request.form.get("symbol"))
            try:
                total = totalq[0]["total"]
            except IndexError:
                total = 'null'
            # if first time, insert information for total stock count
            if total == 'null':
                db.execute("INSERT INTO history (total, user, stock, value, company, price) VALUES (?, ?, ?, ?, ?, ?)", int(shares), id, 
                request.form.get("symbol").lower(), shares*price, stock["name"], price)
            # otherwise just update the existing total count with old total count + new shares bought
            else:
                db.execute("UPDATE history SET total = ?, value = ? WHERE user = ? and stock = ? and time is NULL", int(total) + int(shares),
                (int(total) + int(shares)) * price, id, request.form.get("symbol").lower())
                
            db.execute("UPDATE users SET cash = ? WHERE id = ?", amount - price*shares, id)
       # after purchase take user back to portfolio
       return redirect("/")

    else:
        return render_template("buy.html")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    if request.method == "GET":
        # Querying time stamped information to show history of purchases/sales
        id = session["user_id"]
        info = db.execute("SELECT * FROM history WHERE user = ? and time IS NOT NULL Order by time", id)
        leni = len(info)

        # feed information into history.html for display
        return render_template("history.html", info=info, leni=leni)



@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    # If POST request validate information entered and feed results if valid
    if request.method == "POST":
        # validate entry
        if not request.form.get("symbol"):
            return apology("Please insert a symbol")
        quote = request.form.get("symbol")
        info = lookup(quote)
        # make sure symbols are an actual stock ticker
        if not info:
            return apology("Please insert a valid stock ticker")
        # if it is provide information returned by API
        else:
            price = float(info["price"])
            return render_template("quoted.html", info=info, price=price)
    # If GET request then load template for symbol entry
    else:
        return render_template("quote.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    session.clear()
    if request.method == "POST":
        # validate registration form
        if not request.form.get("username"):
            return apology("must provide a username")
        if not request.form.get("password"):
            return apology("must provide a password")
        if not request.form.get("confirmation"):
            return apology("must provide password confirmation")
        if request.form.get("confirmation") != request.form.get("password"):
            return apology("passwords must match")
        check = db.execute("Select username FROM users")
        lenc = len(check)
        # check existing usernames to make sure its available
        for i in range(0,lenc):
            username = check[i]["username"]
            if request.form.get("username") == username:
                return apology("username taken")
        # generate password hash for database
        hashp = generate_password_hash(request.form.get("password"))
        # insert user information into database
        db.execute("INSERT INTO users (username, hash) VALUES (?,?)", request.form.get("username"), hashp)
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))
        # store session information to log user in after registration
        session["user_id"] = rows[0]["id"]
        # redirect to index after registering
        return redirect("/")
    else:
        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    # setting up information needed for both POST and GET
    id = session["user_id"]
    info = db.execute("SELECT * FROM history WHERE user = ? and time is NULL and total > 0", id)
    leni = len(info)


    if request.method == "POST":
        money = db.execute("SELECT cash FROM users WHERE id = ?", id)
        amount = float(money[0]["cash"])
        stock = request.form.get("symbol")
        shares = request.form.get("shares")
        # validate possible errors
        # make sure shares are numerical
        try:
            float(shares)
        except ValueError:
            return apology("Please insert valid shares")
        shares = float(shares)
        intshares = int(shares)
        # make sure share are an integer
        if intshares != shares:
            return apology("please insert valid shares")
        shares = intshares
        # make sure shares entered are positive
        if shares < 1:
            return apology("please insert valid amount of shares")
        stockinfo = lookup(stock)
        # make sure stock symbol is valid
        if not stockinfo:
            return apology("Please insert a valid stock ticker")
        price = float(stockinfo["price"])
        # load information from database to make sure user has purchaed stock and how much
        info = db.execute("SELECT * FROM history WHERE user = ? and stock = ? and time is NULL", id, stock.lower())
        # make sure user has purchased stock already
        try:
            total = info[0]["total"]
        except IndexError:
            return apology("something went wrong")
        total = int(info[0]["total"])
        # make sure user has enough shares to sell
        if shares > total:
            return apology("You don't own that many shares")
        else:
        # once everything is valid, start updating database(db)
            # user cash will be updated to what they have plus what they sell
            cash = amount + (shares*price)
            time = datetime.now()
            # updates new total shares owned to old total - shares sold
            db.execute("UPDATE history SET total = ? WHERE stock = ? and user = ? and time is NULL", total - shares, stock.lower(), id)
            # updates cash in db
            db.execute("UPDATE users SET cash = ? WHERE id = ?", cash, id)
            # adds sale order information to db
            db.execute("INSERT INTO history (sold, stock, user, time, price) VALUES (?, ?, ?, ?, ?)", -abs(shares), stock.lower(), id, time, price)
            return redirect("/")
    # loads template form for available symbols for sale and share amount entry if GET request
    else:
        return render_template("sell.html", info=info, leni=leni)

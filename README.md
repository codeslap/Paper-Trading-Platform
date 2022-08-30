Ever wanted to practice trading stocks, but don't want to risk losing actual money? 

This web application let's you do just that by allowing you to buy/sell stocks using real-time quotes.

To register for a free API key, use IEX:

Visit https://iexcloud.io/cloud-login#/register/

Select the “Individual” account type, then enter your name, email address, and a password, and click “Create account”.

Once registered, scroll down to “Get started for free” and click “Select Start plan” to choose the free plan.

Once you’ve confirmed your account via a confirmation email, visit https://iexcloud.io/console/tokens.

Copy the key that appears under the Token column (it should begin with pk_).

In your terminal window, execute:

$ export API_KEY=value

Then you can launch an HTTP server locally from your IDE. I am using Visual Studio. All changes will save in the database (db). 

You start with $10,000 upon registration, but you can edit that in the db of course.

Here is the Schema for the database:

![schema](https://user-images.githubusercontent.com/56369460/187427879-45f30077-9349-4620-accb-e0ea9e77d3bc.jpg)

Enjoy, and have fun!

This project is a problem set from Harvard's CS50x course.



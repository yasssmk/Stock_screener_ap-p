import express from "express";
import bodyParser from "body-parser";
import env from "dotenv";
import pkg from 'express-openid-connect';
import { createClient } from '@supabase/supabase-js';
import axios, { Axios } from "axios";
import Stripe from "stripe"

// Env
env.config();

// Express
const app = express();
const port = 3000;

// Auth0
const { auth, requiresAuth } = pkg;

const config = {
  authRequired: false,
  auth0Logout: true,
  secret: process.env.AUTH_SECRET,
  baseURL: 'http://localhost:3000',
  clientID: process.env.AUTH_CLIENT_ID,
  issuerBaseURL: process.env.AUTH_DOMAIN
};

app.use(auth(config));

// Supabase
const supabaseUrl = process.env.sb_url;
const supabaseKey = process.env.sb_api_key;
const supabase = createClient(supabaseUrl, supabaseKey);


// Body Parser
app.use(bodyParser.urlencoded({ extended: true }));

// Static Files
app.use(express.static("views"));

//StripeS

const stripe = Stripe(process.env.STRIPE_KEY);

//functions

async function createUser(name, surname, email, country) {
    try {
        const { data: existingUsers, error: selectError } = await supabase
            .from('users')
            .select("*")
            .eq('Email', email);

        if (selectError) {
            rollbar.error('Error checking user:', selectError);
            throw new Error('Error checking user');
        }

        if (existingUsers.length === 0) {
            // User does not exist, insert new user
            const { data, error: insertError } = await supabase
                .from('users')
                .insert([{ Name: name, Surname: surname, Email: email, Country: country}]);

            if (insertError) {
                rollbar.error('Error registering user:', insertError);
                throw new Error('Error registering user');
            }

            return 'User created successfully';
        }

        return 'User already exists';
    } catch (error) {
        rollbar.error('Error in createUser function:', error);
        throw error; // Propagate the error to be handled in the calling function
    }
}

async function addStockManually(user_id, symbol) {
    try {
        // Check if the stock symbol exists and get its Stock_id
        const { data: stockData, error: stockError } = await supabase
            .from('stocks_list')
            .select("Stock_id")
            .eq('Symbol', symbol)
            .single();

        if (stockError) {
            rollbar.error('Error checking stock:', stockError);
            throw new Error('Error checking stock');
        }

        if (!stockData) {
            return 'The stock does not exist';
        }

        const stock_id = stockData.Stock_id;

        // Check if the stock is already in the user's watchlist
        const { data: existingSymbol, error: selectError } = await supabase
            .from('users_watchlist')
            .select("*")
            .match({ User_id: user_id, Stock_id: stock_id, Plan_id: 2 });

        if (selectError) {
            rollbar.error('Error checking user watchlist:', selectError);
            throw new Error('Error checking user watchlist');
        }

        if (existingSymbol.length === 0) {
            // The stock is not in the user's watchlist, insert it
            const { error: insertError } = await supabase
                .from('users_watchlist')
                .insert([{ User_id: user_id, Stock_id: stock_id, Symbol: symbol,Plan_id: 2 }]);

            if (insertError) {
                rollbar.error('Error adding stock to watchlist:', insertError);
                throw new Error('Error adding stock to watchlist');
            }

            return 'Stock successfully added to user watchlist';
        }

        return 'Stock already exists in user watchlist';
    } catch (error) {
        // Handle any unexpected errors
        rollbar.error('An unexpected error occurred:', error);
        throw error;
    }
}




//Server

app.get('/', async (req, res) => {
    
    if (req.oidc.isAuthenticated()) {
        // Create a user object
        const user = {
            name: req.oidc.user["given_name"],
            surname: req.oidc.user["family_name"],
            email: req.oidc.user["email"],
            country: req.oidc.user["locale"]
        };

        try {
            
            const result = await createUser(user.name, user.surname, user.email, user.country);
            console.log("Ok" + result);

            // Render the index.ejs page with the user object
            res.render("index.ejs", { user: user });
        } catch (error) {
            rollbar.error(error);
            res.status(500).send('An error occurred');
        }
    } else {
        res.render("index.ejs", { user: null });
    }
});


app.get('/profile', requiresAuth(), (req, res) => {
    // res.send(JSON.stringify(req.oidc.user, null, 2));
    res.render("profile.ejs", { user: req.oidc.user["given_name"] });
  });


  app.post('/add', requiresAuth(), async (req, res) => {
    const symbol = req.body.symbol.toUpperCase();
    if (req.oidc.isAuthenticated()) {
        // Extract the email from the authenticated user's information
        const email = req.oidc.user["email"];

        try {
            // Fetch the user's ID from the database
            const { data, error } = await supabase
                .from('users')
                .select("User_id")
                .eq('Email', email)
                .single();

            if (error) {
                throw error;
            }

            if (!data) {
                res.status(404).send('User not found');
                return;
            }

            const user_id = data.User_id;

            // Add the stock to the user's watchlist
            const result = await addStockManually(user_id, symbol);
            console.log("Ok " + result);
            // Redirect or render as needed after successful operation
            res.redirect('/'); // Adjust this as per your requirement
        } catch (error) {
            rollbar.error(error);
            res.status(500).send('An error occurred');
        }
    } else {
        res.redirect("/login");
    }
});


//Payment

app.post('/start-subscription', async (req, res) => {
    const { planId } = req.body;
    try {
        const session = await stripe.checkout.sessions.create({
            payment_method_types: ['card'],
            line_items: [{
                price: planId,
                quantity: 1,
            }],
            mode: 'subscription',
            success_url: 'http://localhost:3000/success?session_id={CHECKOUT_SESSION_ID}',
            cancel_url: 'http://localhost:3000/cancel',
        });

        // Redirect to Stripe Checkout
        return res.redirect(303, session.url);
    } catch (error) {
        console.error('Error creating checkout session:', error);
        return res.status(500).send("Internal Server Error");
    }
});

// Webhook endpoint for Stripe
app.post('/webhook', bodyParser.raw({type: 'application/json'}), (request, response) => {
    const sig = request.headers['stripe-signature'];

    let event;

    try {
        event = stripe.webhooks.constructEvent(request.body, sig, process.env.STRIPE_WEBHOOK_SECRET);
    } catch (err) {
        return response.status(400).send(`Webhook Error: ${err.message}`);
    }

    // Handle the checkout.session.completed event
    if (event.type === 'checkout.session.completed') {
        const session = event.data.object;
        // Implement function to grant access to paid features here
        console.log(`Payment for session ${session.id} successful, for user ${session.customer_email}`);
    }

    response.json({received: true});
});

app.get('/success', async (req, res) => {
    const sessionId = req.query.session_id;
    if (!sessionId) {
        return res.status(400).send("Session ID is missing");
    }

    try {
        const session = await stripe.checkout.sessions.retrieve(sessionId);
        const customer = await stripe.customers.retrieve(session.customer);

        console.log("User email:", customer.email); // Logging the user's email

        // Here you can render a success page or redirect the user
        res.send("Subscription successful! Check your server logs for the user's email.");
    } catch (error) {
        console.error("Error retrieving checkout session:", error);
        res.status(500).send("Internal Server Error");
    }
});



app.listen(port, () => {
    console.log(`Server running on port ${port}`);
  });

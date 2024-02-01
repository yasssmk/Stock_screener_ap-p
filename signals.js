import express from "express";
import axios, { Axios } from "axios";
import bodyParser from "body-parser";
import { createClient } from '@supabase/supabase-js';
import nodemailer from "nodemailer";
import ejs from "ejs"
import env from "dotenv";
import sgMail from '@sendgrid/mail';
import Rollbar from "rollbar";


// Env
env.config();

// Express
const app = express();
const port = 3000;

// Middleware to parse JSON
app.use(bodyParser.json());

//Rollbar
// include and initialize the rollbar library with your access token
var Rollbar = require('rollbar')
var rollbar = new Rollbar({
  accessToken: process.env.RB_TOKEN,
  captureUncaught: true,
  captureUnhandledRejections: true,
})

// record a generic message and send it to Rollbar
rollbar.log('Hello world!')

// Supabase
const supabaseUrl = process.env.sb_url;
const supabaseKey = process.env.sb_api_key;
const supabase = createClient(supabaseUrl, supabaseKey);

//SENDGRID

  sgMail.setApiKey(process.env.SG_API_KEY)


//Functions

async function fetchUserData() {
    try{ 
        const { data: watchlistData, error: watchlistError } = await supabase
            .from('users_watchlist')
            .select('*')

        const { data: usersData, error: usersError } = await supabase
            .from('users')
            .select('*')

        if (watchlistError || usersError) {
            console.error(watchlistError || usersError)
            return null
        }

        return { watchlistData, usersData }; 
    } catch(error){
        rollbar.error(error)
        return null
    }
}


async function processDataEmail(weekly_signals, portfolio) {
    try{
        const userData = await fetchUserData();

        if (!userData) {
            console.error("Failed to fetch user data.");
            return; // Exit if userData is not valid
        }

        // Convert weekly_signals to a more accessible format
        const signalsDict = weekly_signals.reduce((acc, item) => {
            const key = Object.keys(item)[0]; // Get stock ID as key
            acc[key] = item[key]; // Add to dictionary
            return acc;
        }, {});

        // Convert portfolio to a more accessible format
        const portfolioDict = portfolio.reduce((acc, item) => {
            if (!acc[item.Stock_id]) {
                acc[item.Stock_id] = []; // Initialize an array for each stock ID
            }
            acc[item.Stock_id].push(item); // Add portfolio item to the corresponding stock ID array
            return acc;
        }, {});

        // Map user data with watchlist
        let userWatchlists = {};
        userData.watchlistData.forEach(item => {
            if (!userWatchlists[item.User_id]) {
                const user = userData.usersData.find(user => user.User_id === item.User_id);
                if (user) {
                    userWatchlists[item.User_id] = {
                        stocks: [],
                        email: user.Email,
                        name: user.Name,
                    };
                } else {
                    console.error(`User not found for ID: ${item.User_id}`);
                }
            }
            if (userWatchlists[item.User_id]) { // Check if user was found
                userWatchlists[item.User_id].stocks.push(item.Stock_id);
            }
    });

    // Iterate over each user and prepare email content
    for (const userId in userWatchlists) {
        let emailContent = {
            name: userWatchlists[userId].name,
            signals: [],
            portfolio: []
        };

        // Add signals to user's email content
        userWatchlists[userId].stocks.forEach(stockId => {
            if (signalsDict[stockId]) {
                emailContent.signals.push(signalsDict[stockId]);
            }

            // Add portfolio to user's email content
            if (portfolioDict[stockId]) {
                portfolioDict[stockId].forEach(item => emailContent.portfolio.push(item));
            }
        });

        console.log(emailContent);
        sendEmail(userWatchlists[userId].email, emailContent);
    }
    } catch(error){
        rollbar.error(error)
        return null
    }
}




async function sendEmail(emailAdress, emailContent) {
    try{

        const emailHtml = await ejs.renderFile('./views/signals_email.ejs', emailContent)

        const msg = {
            to: emailAdress,
            from: process.env.SENDER_EMAIL,
            subject: 'Weekly Stock Signals and Portfolio Update',
            
            html: emailHtml,
        }
        sgMail
            .send(msg)
            .then(() => {
            console.log('Email sent')
            })
            .catch((error) => {
            console.error(error)
            })
    } catch(error){
        rollbar.error(error)
        return null
    }   
}


// Endpoint to receive signals
app.post('/receive-signals', async (req, res) => {
    try{
        signals = await req.body;
        portfolio = await supabase
            .from('portfolio')
            .select()
        processDataEmail(signals, portfolio.data);

        res.status(200).send("Signals received and processing initiated");
    } catch(error){
        rollbar.error(error)
        return null
    }  

});


app.listen(port, () => {
    console.log(`Server running on port ${port}`);
  });

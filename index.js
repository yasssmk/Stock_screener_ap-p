import express from "express";
import bodyParser from "body-parser";
import env from "dotenv";
import pkg from 'express-openid-connect';
import { createClient } from '@supabase/supabase-js';

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

//function create user

async function createUser(name, surname, email, country) {
    try {
        const { data: existingUsers, error: selectError } = await supabase
            .from('users')
            .select("*")
            .eq('Email', email);

        if (selectError) {
            console.error('Error checking user:', selectError);
            throw new Error('Error checking user');
        }

        if (existingUsers.length === 0) {
            // User does not exist, insert new user
            const { data, error: insertError } = await supabase
                .from('users')
                .insert([{ Name: name, Surname: surname, Email: email, Country: country }]);

            if (insertError) {
                console.error('Error registering user:', insertError);
                throw new Error('Error registering user');
            }

            return 'User created successfully';
        }

        return 'User already exists';
    } catch (error) {
        console.error('Error in createUser function:', error);
        throw error; // Propagate the error to be handled in the calling function
    }
}


app.get('/', async (req, res) => {
    if (req.oidc.isAuthenticated()) {
        res.redirect("/profile");
        try {
            const name = req.oidc.user["given_name"];
            const surname = req.oidc.user["family_name"];
            const email = req.oidc.user["email"];
            const country = req.oidc.user["locale"];
    
            const result = await createUser(name, surname, email, country);
            console.log("Ok" + result);
            res.oidc.login({ returnTo: '/profile' });
        } catch (error) {
            console.error(error);
            res.status(500).send('An error occurred');
        }
        console.log(req.oidc.user);
    } else {
        res.render("index.ejs");}
    })


app.get('/profile', requiresAuth(), (req, res) => {
    // res.send(JSON.stringify(req.oidc.user, null, 2));
    res.render("profile.ejs", { user: req.oidc.user["given_name"] });
  });

  


// app.get("/login", (req, res) => {
//     if (req.oidc.isAuthenticated()) {
//         res.redirect("/profile");
//         console.log(req.oidc.user);
//     } else {
//         res.render("login.ejs");}
// })

  
// app.get("/register", async (req, res) => {
//     res.redirect('/register');
//     });
  

// app.get('/profile', requiresAuth(), (req, res) => {
//     // Assuming you want to display user information on the profile page
//     res.render("profile.ejs", { user: req.oidc.user["given_name"] });
//   });


app.listen(port, () => {
    console.log(`Server running on port ${port}`);
  });


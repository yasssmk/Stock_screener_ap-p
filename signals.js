import express from "express";
import axios, { Axios } from "axios";
import bodyParser from "body-parser";


// Express
const app = express();
const port = 3000;

// Middleware to parse JSON

app.use(bodyParser.json());

//Fetch signals

async function fetchSignalsAndSendEmails() {
    try {
        // Replace with the URL where your Flask app is hosted
        const response = await axios.get('http://localhost:5000/get-signals');
        const signalsList = response.data;

        console.log(signalsList)

    } catch (error) {
        console.error('Error fetching signals:', error);
    }
}

function sendEmail(signalData) {
    console.log("Sending emails based on:", signalData);
    // Implement email sending logic here
}


// Endpoint to receive signals
app.post('/receive-signals', (req, res) => {
    const signals = req.body;
    // Call the function to send emails
    sendEmail(signals);

    res.status(200).send("Signals received and processing initiated");
});


app.listen(port, () => {
    console.log(`Server running on port ${port}`);
  });

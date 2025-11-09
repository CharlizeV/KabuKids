// server.js
require('dotenv').config();
const express = require('express');
const connectDB = require('./db'); //
const User = require('./models/User'); //
const Meal = require('./models/Meal'); //

const app = express();
app.use(express.json()); // Middleware to read JSON from requests

// 1. Connect to the database
connectDB();

// --- Define API Endpoints ---

// Endpoint for User Login
app.post('/login', async (req, res) => {
  console.log("\n--- Login attempt received! ---"); 
  
  // Check if req.body exists
  if (!req.body) {
    console.log("ERROR: req.body is empty. Is express.json() middleware missing?"); 
    return res.status(400).send('Bad request: no body');
  }

  const { username, password } = req.body;

  console.log("Received body:", req.body); 
  console.log("Searching for user:", username); 

  try {
    const user = await User.findOne({ username: username, password: password });

    if (user) {
      console.log("SUCCESS: User found:", user.username); 
      res.json(user); // Send user data back if login is successful
    } else {
      console.log("FAILURE: Invalid username or password."); 
      res.status(401).send('Invalid username or password');
    }
  } catch (err) {
    console.log("ERROR: Database query failed:", err.message); 
    res.status(500).send('Server error');
  }
});

// Endpoint to get meals for a specific user
app.get('/meals/:userId', async (req, res) => {
  try {
    const meals = await Meal.find({ userId: req.params.userId });
    res.json(meals);
  } catch (err) {
    res.status(500).send('Error fetching meals');
  }
});

// Endpoint to create a new meal
app.post('/meals', async (req, res) => {
  try {
    const newMeal = new Meal({
      userId: req.body.userId,
      transcript: req.body.transcript,
      // ...add other fields from your model
      date: new Date()
    });
    await newMeal.save();
    res.status(201).json(newMeal);
  } catch (err) {
    res.status(500).send('Error creating meal');
  }
});


// 3. Start the server
const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`Server running on http://localhost:${PORT}`);
});
// index.js
const express = require('express');
const fetch = require('node-fetch'); // npm install node-fetch@2
const path = require('path');

const app = express();
const PORT = process.env.PORT || 3000;

// Serve static files from /public
app.use(express.static(path.join(__dirname, 'public')));

// Simple hello endpoint
app.get('/api/hello', (req, res) => {
  res.json({ message: 'Hello, world!' });
});

// IP endpoint
app.get('/api/ip', async (req, res) => {
    try {
        const response = await fetch('https://dataram57.com/ip/');
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        const data = await response.text(); // assuming the endpoint returns plain text
        res.json({ ip: data.trim() });
    } catch (error) {
        console.error(error);
        res.status(500).json({ error: 'Failed to fetch IP' });
    }
});

// Start server
app.listen(PORT, () => {
    console.log(`Server running on http://localhost:${PORT}`);
});
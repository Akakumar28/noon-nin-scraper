const express = require('express');
const cors = require('cors');
const axios = require('axios');
const cheerio = require('cheerio');
const path = require('path');

const app = express();
const PORT = process.env.PORT || 5000;

// Middleware
app.use(cors());
app.use(express.json());

// Helper function to get product URL
const getNoonProductUrl = (ninCode, country) => {
  return `https://www.noon.com/${country}-en/search/?q=${ninCode}`;
};

// Scrape search results to find product link
async function findProductLink(ninCode, country) {
  try {
    const searchUrl = getNoonProductUrl(ninCode, country);
    console.log(`Fetching search results from: ${searchUrl}`);
    
    const response = await axios.get(searchUrl, {
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36',
        'Accept-Language': 'en-US,en;q=0.9',
      }
    });
    
    const $ = cheerio.load(response.data);
    
    // Search for product link that contains the NIN code
    const productLinks = $('a[href*="/p/"]');
    let productUrl = null;
    
    productLinks.each((i, element) => {
      const href = $(element).attr('href');
      if (href && href.includes(ninCode)) {
        productUrl = `https://www.noon.com${href}`;
        return false; // Break the loop
      }
    });
    
    return productUrl;
  } catch (error) {
    console.error(`Error finding product link for ${ninCode}:`, error.message);
    return null;
  }
}

// Scrape product details page
async function scrapeProductDetails(productUrl) {
  try {
    console.log(`Fetching product details from: ${productUrl}`);
    
    const response = await axios.get(productUrl, {
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36',
        'Accept-Language': 'en-US,en;q=0.9',
      }
    });
    
    const $ = cheerio.load(response.data);
    
    // Extract product name
    const name = $('h1').text().trim();
    
    // Extract product images
    const images = [];
    $('div.gallery-slider img').each((i, element) => {
      const imageUrl = $(element).attr('src');
      if (imageUrl) {
        // Remove format and width parameters to get high-res version
        const highResUrl = imageUrl.split('?')[0];
        images.push({ 
          url: highResUrl, 
          isHighRes: true 
        });
      }
    });
    
    // If main image slider doesn't work, try alternate image containers
    if (images.length === 0) {
      $('picture img, .swiper-slide img').each((i, element) => {
        const imageUrl = $(element).attr('src');
        if (imageUrl && !images.some(img => img.url === imageUrl.split('?')[0])) {
          const highResUrl = imageUrl.split('?')[0];
          images.push({ 
            url: highResUrl, 
            isHighRes: true 
          });
        }
      });
    }
    
    return { name, images, productUrl };
  } catch (error) {
    console.error(`Error scraping product details:`, error.message);
    return null;
  }
}

// API endpoint to scrape products from Noon
app.post('/api/scrape', async (req, res) => {
  const { ninCodes, country } = req.body;
  
  if (!ninCodes || !Array.isArray(ninCodes) || ninCodes.length === 0) {
    return res.status(400).json({ 
      success: false, 
      error: 'Please provide an array of NIN codes' 
    });
  }
  
  try {
    const products = [];
    
    for (const ninCode of ninCodes) {
      console.log(`Processing NIN code: ${ninCode}`);
      
      try {
        // Step 1: Find product link from search results
        const productUrl = await findProductLink(ninCode, country);
        
        if (!productUrl) {
          console.log(`Product URL not found for NIN code: ${ninCode}`);
          products.push({
            ninCode,
            name: `Product not found for ${ninCode}`,
            productUrl: getNoonProductUrl(ninCode, country),
            images: []
          });
          continue;
        }
        
        // Step 2: Scrape product details
        const productDetails = await scrapeProductDetails(productUrl);
        
        if (!productDetails) {
          console.log(`Failed to scrape details for NIN code: ${ninCode}`);
          products.push({
            ninCode,
            name: `Failed to scrape details for ${ninCode}`,
            productUrl,
            images: []
          });
          continue;
        }
        
        products.push({
          ninCode,
          name: productDetails.name,
          productUrl,
          images: productDetails.images
        });
        
        console.log(`Successfully scraped ${ninCode}: ${productDetails.name}`);
      } catch (error) {
        console.error(`Error processing ${ninCode}:`, error.message);
        products.push({
          ninCode,
          name: `Error: ${error.message}`,
          productUrl: getNoonProductUrl(ninCode, country),
          images: []
        });
      }
    }
    
    res.json({ success: true, products });
  } catch (error) {
    console.error('Error scraping products:', error.message);
    res.status(500).json({ 
      success: false, 
      error: 'Failed to scrape products. Please try again later.' 
    });
  }
});

// Serve static files in production
if (process.env.NODE_ENV === 'production') {
  app.use(express.static(path.join(__dirname, '../../dist')));
  
  app.get('*', (req, res) => {
    res.sendFile(path.join(__dirname, '../../dist/index.html'));
  });
}

app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
});

module.exports = app;

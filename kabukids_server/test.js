const connectDB = require('./db');
const User = require('./models/User');
const Meal = require('./models/Meal');

async function run() {
  await connectDB();

  const user = await User.create({
    name: 'Yuri',
    username: 'yuri123',
    password: '12345',
    age: 22,
    birthday: new Date('2003-06-08'),
    likes: ['rice', 'chicken'],
    dislikes: ['broccoli']
  });
  console.log('User added:', user.name);

  const meal1 = await Meal.create({
    userId: user._id,
    startTime: new Date('2025-11-08T12:30:00'),
    endTime: new Date('2025-11-08T13:00:00'),
    date: new Date('2025-11-08T12:30:00'),
    transcript: 'Chicken salad.',
    conversationSuggestions: ['Talk about healthy food.'],
    ingredientSuggestions: ['Lettuce', 'Tomato', 'Chicken']
  });
  console.log('Meal 1 added for user:', user.username);
  
  const meal2 = await Meal.create({
    userId: user._id,
    startTime: new Date('2025-11-07T09:00:00'),
    endTime: new Date('2025-11-07T09:15:00'),
    date: new Date('2025-11-07T09:00:00'),
    transcript: 'Cereal for breakfast.',
    conversationSuggestions: ['Talk about the user\'s morning.'],
    ingredientSuggestions: ['Milk', 'Oats']
  });
  console.log('Meal 2 added for user:', user.username);

  process.exit();
}

run();
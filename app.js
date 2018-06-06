/*
    Heizung
    
    Copyright (C) 2018 Mandl

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */

const fs = require('fs');
const child_process = require('child_process');
const express = require('express');
const passport = require('passport');
const Strategy = require('passport-local').Strategy;
const path = require('path');
const db = require('./db');
const jsonBody = require('body/json');
const Rest = require('connect-rest');
const bodyParser = require('body-parser');
const logger = require('./logger');
const { spawn } = require('child_process');



var handlebars = require('express-handlebars')
.create({
    defaultLayout: 'main',
    helpers: {
        section: function (name, options) {
            if (!this._sections) {
                this._sections = {};
            }
            this._sections[name] = options.fn(this);
            return null;
        },
        //2018-05-30_17_15_53.396682.jpg
        formatTimeTwc:function(strTime) {
        	strTime = strTime.toString();
            return strTime.substr(0,9) + '    ' + strTime.substr(11,8).replace(/_/g, ':') ;
        }
    }
});



// Configure the local strategy for use by Passport.
//
// The local strategy require a `verify` function which receives the credentials
// (`username` and `password`) submitted by the user. The function must verify
// that the password is correct and then invoke `cb` with a user object, which
// will be set at `req.user` in route handlers after authentication.
passport.use(new Strategy(function(username, password, cb) {
	db.users.findByUsername(username, function(err, user) {
		if (err) {
			return cb(err);
		}
		if (!user) {
			return cb(null, false);
		}
		if (user.password != password) {
			return cb(null, false);
		}
		return cb(null, user);
	});
}));

// Configure Passport authenticated session persistence.
//
// In order to restore authentication state across HTTP requests, Passport needs
// to serialize users into and deserialize users out of the session. The
// typical implementation of this is as simple as supplying the user ID when
// serializing, and querying the user record by ID from the database when
// deserializing.
passport.serializeUser(function(user, cb) {
	cb(null, user.id);
});

passport.deserializeUser(function(id, cb) {
	db.users.findById(id, function(err, user) {
		if (err) {
			return cb(err);
		}
		cb(null, user);
	});
});

// Create a new Express application.
var app = express();

app.disable('x-powered-by');

// Use application-level middleware for common functionality, including
// logging, parsing, and session handling.
// app.use(require('morgan')('dev'));
app.use(require('cookie-parser')());
app.use(bodyParser.urlencoded({ extended : true }));
app.use(require('express-session')({
	secret : 'keyboard cat',
	resave : false,
	saveUninitialized : false
}));


// Initialize Passport and restore authentication state, if any, from the
// session.
app.use(passport.initialize());
app.use(passport.session());

// static routes


app.use('/picture',require('connect-ensure-login').ensureLoggedIn(),express.static(__dirname + '/picture',{ maxAge: '30 days' }))

// view engine
app.engine('handlebars', handlebars.engine);
app.set('view engine', 'handlebars');


app.get('/login', function(req, res) {
	 res.sendFile(path.join(__dirname, 'public','login.html'));
});

// renter main page
app.get('/', require('connect-ensure-login').ensureLoggedIn(), function(req, res) {
	
	res.render('live', { layout:'main', title: 'Live view'});
	child.stdin.write('reload\n');
});

//renter log page
app.get('/log', require('connect-ensure-login').ensureLoggedIn(), function(req, res) {
	var logtext = fs.readFileSync(path.join(__dirname, 'temp.log'),'utf8')
	
	logtext = logtext.replace(/\n/g,'<br>');

	res.render('logfile', { layout:'main', title: 'Log', logdata:logtext});

});

// render motion page
app.get('/motion', require('connect-ensure-login').ensureLoggedIn(), function(req, res) {
	var files = fs.readdirSync(path.join(__dirname,'/picture','motion'));
	var motionFiles = {"data":[]};;
	for( i in files)
	{
		var me = {"name":files[i],"date":""};
		motionFiles.data.push(me);
	}	
	
	//console.log(motionFiles);
	res.render('motion', { layout:'main', title: 'Motion',fileNames:motionFiles});
});


// Clear all pictures
app.get('/clearPicture', require('connect-ensure-login').ensureLoggedIn(), function(req, res) {
	
	try {
	fs.readdir(path.join(__dirname,'picture','motion'), (err, files) => {
		  if (err) throw err;

		  for (const file of files) {
		    fs.unlinkSync(path.join(__dirname, 'picture','motion', file));
		  }
		});
	} 
	catch (ex){
		console.log(ex);
		
	}
	res.send('ok');
	res.end();		
});

// save new ROI
app.get('/save', require('connect-ensure-login').ensureLoggedIn(), function(req, res) {
		
	var startX = req.query.startX;
	var startY = req.query.startY;
	var w = req.query.w;
	var h = req.query.h;
	
	if ((startX != null) && (startY != null) && (w != null) && ( h != null))
	{
		console.log(startX,startY,w,h); 
		child.stdin.write('roi,' + startX + ',' + startY + ',' + w + ',' + h +'\n');
	}
	res.send('ok');
	res.end();		
});


// delete log
app.get('/deleteLog', require('connect-ensure-login').ensureLoggedIn(), function(req, res) {
	
	fs.writeFileSync(path.join(__dirname,'temp.log'),"");
	res.send('ok');
	res.end();		
});

// Login
app.post('/login', passport.authenticate('local', {
	failureRedirect : '/login'
}), function(req, res) {
	res.redirect('/');
});

// logout from server
app.get('/logout', function(req, res) {
	req.logout();
	res.redirect('/');
});

// Handle 404
app.use(function(req, res, next) {
	res.redirect('/');
    
});

app.listen(3000, function () {
	  logger.info('Motion listening on port 3000!');
});

process.on('exit', function(code) {
	child.kill('SIGHUP')
});

// start motion.py
child = spawn('python3', ['-u','motion.py']);
//child = spawn('python3', ['motion.py']);

child.stdout.on('data', (data) => {
	  console.log(`child stdout: ${data}`);
});

child.stderr.on('data', (data) => {
  console.log(`child stderr: ${data}`);
  logger.info(data);
});


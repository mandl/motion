/*
    Heizung

    Copyright (C) 2018-2019 Mandl

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
const express = require('express');
const path = require('path');
const jsonBody = require('body/json');
//const Rest = require('connect-rest');
const bodyParser = require('body-parser');
const { logger, logfolder} = require('./logger');
const configData = require('./config.json');

const showImageCount = 99;
var dayFolder;
var recentIndex = 0;


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
        // 2018-05-30_17_15_53.396682.jpg
        formatTimeTwc:function(strTime) {
        	strTime = strTime.toString();
            return strTime.substr(0,10) + '    ' + strTime.substr(11,8).replace(/_/g, ':') ;
        }
    }
});


// Create a new Express application.
var app = express();

app.disable('x-powered-by');

// Use application-level middleware for common functionality, including
// logging, parsing, and session handling.
app.use(require('morgan')('dev'));
app.use(require('cookie-parser')());
app.use(bodyParser.urlencoded({ extended : true }));
app.use(require('express-session')({
	secret : 'keyboard cat',
	resave : false,
	saveUninitialized : false
}));

// static routes
app.use(express.static(__dirname+'/public'));

var files = fs.readdirSync(path.join(__dirname,'picture','motion'));
dayFolder = files[files.length-1];

logger.info(dayFolder);

app.use('/picture',express.static(__dirname + '/picture',{ maxAge: '30 days' }))

// view engine
app.engine('handlebars', handlebars.engine);
app.set('view engine', 'handlebars');


// renter main page
app.get('/', function(req, res) {

    res.render('live', { layout:'main', title: 'Live view',camname:'cam1'});

});

// renter main page
app.get('/cam1view', function(req, res) {

    res.render('live', { layout:'main', title: 'Live view',camname:'cam1'});

});

//renter cam page
app.get('/cam2view', function(req, res) {

  res.render('live', { layout:'main', title: 'Live view',camname:'cam2'});

});

//renter cam page
app.get('/cam3view', function(req, res) {

   res.render('live', { layout:'main', title: 'Live view',camname:'cam3'});

});

// renter log page
app.get('/log', function(req, res) {
	var logtext = fs.readFileSync(logfolder(),'utf8')
	logtext = logtext.replace(/\n/g,'<br>');

	res.render('logfile', { layout:'main', title: 'Log', logdata:logtext});

});

// renter admin page
app.get('/admin', function(req, res) {

	res.render('admin', { layout:'main', title: 'Admin',level:"",area:"",threshold:""});

});

// admin data
app.post('/admindata', function(req, res) {

	var annotate=req.body.annotate;
	var level=req.body.level;
	var threshold=req.body.threshold;
	var area=req.body.area;

	res.redirect('/');
});

// render motion page
app.get('/motion', function(req, res) {
	var day = req.query.day;
	var index = req.query.index;
	var n = 0;
	if (day == null)
	{
		day= dayFolder;
	}
	else
	{
		dayFolder=day;
	}
	if (index == null)
	{
		index= recentIndex;
	}
	else
	{
		recentIndex = index;
	}
	n = index * showImageCount;
	try {
	    var files = fs.readdirSync(path.join(__dirname,'picture','motion',day));
	    var pagiCount = files.length / showImageCount;
	    var motionFiles = {"data":[]};
	    var FileCount = files.length;
	    var minFiles = files.slice(n,n + showImageCount);
	    for( i in minFiles)
	    {
		    var me = {"name":minFiles[i],"folder":day};
		    motionFiles.data.push(me);
	    }
	    var nextIndex = parseInt(index, 10) + 1;
	    var prevIndex = parseInt(index, 10) - 1;
	    res.render('motion', { layout:'main', title: 'Motion',fileNames:motionFiles, fileCount:FileCount,fileStart:n,fileStop:n+showImageCount,day:day,index:nextIndex,prevIndex:prevIndex,pagiCount:pagiCount});
        }
	catch (e) {
		res.render('motion', { layout:'main', title: 'Motion'});
	}
});

// Clear all pictures
app.get('/clearPicture', function(req, res) {

	try {
	var day = req.query.day;
	if (day == null)
	{
		day= dayFolder;
	}
	fs.readdir(path.join(__dirname,'picture','motion',day), (err, files) => {
		  if (err) throw err;

		  for (const file of files) {
		    fs.unlinkSync(path.join(__dirname, 'picture','motion',day, file));
		  }
		});
	}
	catch (ex){
		logger.error(ex);
	}
	setTimeout(function(){
		res.send('ok');
		res.end();
	}, 10 * 1000);
});

// render motion days page
app.get('/motiondays', function(req, res) {

	var files = fs.readdirSync(path.join(__dirname,'picture','motion'));
	var motionFiles = {"data":[]};
	for( i in files)
	{
		var me = {"name":files[i]};
		motionFiles.data.push(me);
	}

	// console.log(motionFiles);
	res.render('motiondays', { layout:'main', title: 'Days',fileNames:motionFiles});
});

// save new ROI
app.get('/save', function(req, res) {
		
	var cam = req.query.cam;
	var startX = req.query.startX;
	var startY = req.query.startY;
	var w = req.query.w;
	var h = req.query.h;
	
	if ((startX != null) && (startY != null) && (w != null) && ( h != null))
	{
		// console.log(startX,startY,w,h);
		if( cam=='CAMPI')
		{
			child.stdin.write('roi,' + startX + ',' + startY + ',' + w + ',' + h +'\n');
		}
		if( cam=="CAM1")
		{
			childStream1.stdin.write('roi,' + startX + ',' + startY + ',' + w + ',' + h +'\n');
		}
		if( cam=="CAM2")
		{
			childStream2.stdin.write('roi,' + startX + ',' + startY + ',' + w + ',' + h +'\n');
		}
		if( cam=="CAM3")
		{
			childStream3.stdin.write('roi,' + startX + ',' + startY + ',' + w + ',' + h +'\n');
		}
	}
	res.send('ok');
	res.end();		
});

// set motion day
app.get('/setmotiondays', function(req, res) {
	
	dayFolder = req.query.day;
	res.send('ok');
	res.end();		
});

// delete log
app.get('/deleteLog', function(req, res) {
	
	fs.writeFileSync(logfolder(),"");
	res.send('ok');
	res.end();		
});

// Handle 404
app.use(function(req, res, next) {
	res.redirect('/');
    
});

app.listen(3000, function () {
	  logger.info('Motion listening on port 3000!');
});



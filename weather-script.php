<?php

require_once('/var/www/html/jpgraph-4.4.1/src/jpgraph.php');
require_once('/var/www/html/jpgraph-4.4.1/src/jpgraph_line.php');
require_once('/var/www/html/jpgraph-4.4.1/src/jpgraph_scatter.php');
require_once('/var/www/html/jpgraph-4.4.1/src/jpgraph_regstat.php');
date_default_timezone_set('Europe/Berlin');

DEFINE("TTF_DIR", "/var/www/html/");

header('Content-Type: text/html; charset=UTF-8');


function reorder_array(&$array, $new_order)
{
	$inverted = array_flip($new_order);
	uksort($array, function ($a, $b) use ($inverted) {
		return $inverted[$a] > $inverted[$b];
	});
}

// Zugangsdaten Netatmo

$bearertoken = getenv('BEARER_TOKEN');

$headers = array(
	"Content-Type: application/json",
	"Authorization: Bearer " . $bearertoken
);


// Anfrage mit Bearer Token

$params		= null;
$params		= json_decode($response, true);
$api_url	= "https://api.netatmo.net/api/devicelist";


// Daten abrufen

$ch = curl_init();
curl_setopt($ch, CURLOPT_URL, $api_url);
curl_setopt($ch, CURLOPT_HTTPHEADER, $headers);
curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
#print_r($ch);
$array = curl_exec($ch);
curl_close($ch);




// Messwerte bereitstellen

$netatmo = json_decode($array, true);
$modules = array();

$dt = new DateTime();


//=====================================================
//Graph erzeugen	
$end = time();
$begin =  time() - 21600;

//echo $time;


$params		     = null;
$params	         = json_decode($response, true);
$device_id       = getenv('DEVICE_ID');
$outdoormoduleID = getenv('OUTDOOMODULE_ID');
$api_url	= "https://api.netatmo.net/api/getmeasure" .
	"&device_id=" . $device_id .
	"&module_id=" . $outdoormoduleID .
	"&scale=1hour" .
	"&type=temperature" .
	"&date_begin=" . $begin   .
	"&date_end=" . $end;


// Daten abrufen

$ch = curl_init();
curl_setopt($ch, CURLOPT_URL, $api_url);
curl_setopt($ch, CURLOPT_HTTPHEADER, $headers);
curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
$array = curl_exec($ch);
#print_r($ch);
curl_close($ch);

// Messwerte bereitstellen
$netatmolast6h	= json_decode($array, true);

$ydata = array(
	$netatmolast6h["body"][0]["value"][0][0],
	$netatmolast6h["body"][0]["value"][1][0],
	$netatmolast6h["body"][0]["value"][2][0],
	$netatmolast6h["body"][0]["value"][3][0],
	$netatmolast6h["body"][0]["value"][4][0],
	$netatmolast6h["body"][0]["value"][5][0]
);


$xdata = array(0, 1, 2, 3, 4, 5);


$hourstart = date("H") - 5;
$tickPositionsx = array();
$tickLabelsx = array();

for ($i = 0; $i < 7; ++$i) {
	$tickPositionsx[$i] = $i;
	$tickLabelsx[$i] = $hourstart + $i . '';
}

$tickPositionsy = array();
$tickLabelsy = array();

for ($i = 0; $i < 7; ++$i) {
	$tickPositionsy[$i] = $i;
	$tickLabelsy[$i] = $i . SymChar::Get('degree');
}



// Get the interpolated values by creating
// a new Spline object.
$spline = new Spline($xdata, $ydata);

// For the new data set we want 40 points to
// get a smooth curve.
list($newx, $newy) = $spline->Get(30);

// Create the graph
$g = new Graph(266, 250);
$g->img->SetTransparent("white");

$g->clearTheme();
$g->SetMargin(40, 30, 10, 10);
//$g->SetMarginColor('White:0.6'); 
//$g1->SetFrame(true,'White:0.6',1);

$g->SetFrame(false);
$g->SetFrame(true, 'black', 0);

$g->img->SetAntiAliasing(false);

$g->SetScale('intlin');

$g->xaxis->SetPos("min");

$g->yaxis->scale->SetGrace(100, 100);
$g->xaxis->SetMajTickPositions($tickPositionsx, $tickLabelsx);
$g->yaxis->SetLabelFormatString('%.1f' . SymChar::Get('degree'));

$g->yaxis->HideTicks(true, true);

//$g->xaxis->HideFirstLastLabel(); 
$g->yaxis->HideFirstLastLabel();

$g->yaxis->HideLine();
$g->xaxis->HideLine();
$g->xaxis->HideTicks();

$g->SetUserFont('Asap-Medium.ttf');
$g->xaxis->SetFont(FF_USERFONT, FS_NORMAL, 11);
$g->yaxis->SetFont(FF_USERFONT, FS_NORMAL, 11);

$splot = new ScatterPlot($ydata, $xdata);

$lplot = new LinePlot($newy, $newx);
$lplot->SetColor('navy');
$lplot->SetWeight(5);


$g->Add($lplot);

$g->Stroke('6h.png');

//=====================================================	

for ($i = 0; $i < sizeof($netatmo["body"]["modules"]); $i++) {
	$name			= $netatmo["body"]["modules"][$i]["module_name"];
	$battery_vp		= $netatmo["body"]["modules"][$i]["battery_vp"];
	$rf_status		= $netatmo["body"]["modules"][$i]["rf_status"];
	$temp			= number_format($netatmo["body"]["modules"][$i]["dashboard_data"]["Temperature"], 1, ".", "");
	$temp_trend		= $netatmo["body"]["modules"][$i]["dashboard_data"]["temp_trend"];
	$humidity		= $netatmo["body"]["modules"][$i]["dashboard_data"]["Humidity"];
	$co2			= $netatmo["body"]["modules"][$i]["dashboard_data"]["CO2"];
	$min_temp		= number_format($netatmo["body"]["modules"][$i]["dashboard_data"]["min_temp"], 1, ".", "");
	$min_time		= $dt->setTimestamp($netatmo["body"]["modules"][$i]["dashboard_data"]["date_min_temp"])->format('H:i');
	$max_temp		= number_format($netatmo["body"]["modules"][$i]["dashboard_data"]["max_temp"], 1, ".", "");
	$max_time		= $dt->setTimestamp($netatmo["body"]["modules"][$i]["dashboard_data"]["date_max_temp"])->format('H:i');
	$measure_time 	= $dt->setTimestamp($netatmo["body"]["modules"][$i]["dashboard_data"]["time_utc"])->format('H:i');

	$battery_status = "full";
	if ($netatmo["body"]["modules"][$i]["type"] = "NAModule1") {  //outdoor

		if ($battery_vp < 5000 and $battery_vp > 4500) {
			$battery_status = "half";
		} elseif ($battery_vp <= 4500 and $battery_vp > 4000) {
			$battery_status = "low";
		} elseif ($battery_vp <= 4000) {
			$battery_status = "empty";
		}
	} else {  //indoor

		if ($battery_vp < 5280 and $battery_vp > 4920) {
			$battery_status = "half";
		} elseif ($battery_vp <= 4920 and $battery_vp > 4560) {
			$battery_status = "low";
		} elseif ($battery_vp <= 4560) {
			$battery_status = "empty";
		}
	}

	$t_array = array(
		"name" => $name,
		"battery_status" => $battery_status,
		"rf_status" => $rf_status,
		"temp" => $temp,
		"temp_trend" => $temp_trend,
		"humidity" => $humidity,
		"min_temp" => $min_temp,
		"min_time" => $min_time,
		"max_temp" => $max_temp,
		"max_time" => $max_time,
		"co2" => $co2,
		"last measure_time" => $measure_time
	);

	array_push($modules, $t_array);
}

$base_name			= $netatmo["body"]["devices"]["0"]["module_name"];
$base_calibrating	= $netatmo["body"]["devices"]["0"]["co2_calibrating"];
$base_wifi_status	= $netatmo["body"]["devices"]["0"]["wifi_status"];
$base_temp			=  number_format($netatmo["body"]["devices"]["0"]["dashboard_data"]["Temperature"], 1, ".", "");
$base_temp_trend	= $netatmo["body"]["devices"]["0"]["dashboard_data"]["temp_trend"];
$base_humidity		= $netatmo["body"]["devices"]["0"]["dashboard_data"]["Humidity"];
$base_pressure		= $netatmo["body"]["devices"]["0"]["dashboard_data"]["Pressure"];
$base_pressure_trend = $netatmo["body"]["devices"]["0"]["dashboard_data"]["pressure_trend"];
$base_CO2			= $netatmo["body"]["devices"]["0"]["dashboard_data"]["CO2"];
$base_min_temp		= number_format($netatmo["body"]["devices"]["0"]["dashboard_data"]["min_temp"], 1, ".", "");
$base_min_time		= $dt->setTimestamp($netatmo["body"]["devices"]["0"]["dashboard_data"]["date_min_temp"])->format('H:i');
$base_max_temp		= number_format($netatmo["body"]["devices"]["0"]["dashboard_data"]["max_temp"], 1, ".", "");
$base_max_time		= $dt->setTimestamp($netatmo["body"]["devices"]["0"]["dashboard_data"]["date_max_temp"])->format('H:i');
$base_measure_time	= $dt->setTimestamp($netatmo["body"]["devices"]["0"]["dashboard_data"]["time_utc"])->format('H:i');


$t_array = array(
	"name" => $base_name,
	"battery_status" => "charging",
	"rf_status" => "0",
	"temp" => $base_temp,
	"temp_trend" => $base_temp_trend,
	"humidity" => $base_humidity,
	"pressure" => $base_pressure,
	"min_temp" => $base_min_temp,
	"min_time" => $base_min_time,
	"max_temp" => $base_max_temp,
	"max_time" => $base_max_time,
	"co2" => $base_CO2,
	"last measure_time" => $base_measure_time
);

array_push($modules, $t_array);

reorder_array($modules, array(2, 0, 1, 3));

$modulessorted = array();

foreach ($modules as $key => $value) {
	array_push($modulessorted, $value);
}

$modules = $modulessorted;


//print_r($modules);

$url = "http://api.openweathermap.org/data/2.5/weather?id=6940468&lang=en&units=metric&APPID=951ffbd4db78f3909777ee2c0431da5e";

$contents = file_get_contents($url);
$clima = json_decode($contents);

$icon = $clima->weather[0]->icon;


$conditionmapping = array(
	//clear sky
	"01d" => ".",
	"01n" => "O",

	//few clouds
	"02d" => "#",
	"02n" => "§",

	//scattered clouds
	"03d" => "b",
	"03n" => "b",

	// broken clouds
	"04d" => "4",
	"04n" => "4",

	//shower rain
	"09d" => ":",
	"09n" => ":",

	//rain
	"10d" => ")",
	"10n" => "I",

	//thunderstorm
	"11d" => "/",
	"11n" => "M",

	//snow
	"13d" => "<",
	"13n" => "<",


	//mist
	"50d" => "B",
	"50n" => "B"
);



// Variablen

$filename	= "weather-script-output.png";
$font_text_m = "Asap-Medium.ttf";
$font_text_b = "Asap-Bold.ttf";
$font_symbol		= "WeatherIcons-fixed.ttf";


// Leere PNG-Datei mit weißem Hintergrund erstellen

$image		= ImageCreateTrueColor(800, 600);
$background_white	= ImageColorAllocate($image, 255, 255, 255);
$background_black	= ImageColorAllocate($image, 0, 0, 0);

ImageFilledRectangle($image, 0, 0, 800, 300, $background_white);
ImageFilledRectangle($image, 401, 301, 800, 600, $background_black);


// Farbe für Schrift und Hilfslinien festlegen

$color_black		= ImageColorAllocate($image, 0, 0, 0);
$color_white		= ImageColorAllocate($image, 255, 255, 255);
$color_grey		= ImageColorAllocate($image, 200, 200, 200);
$color_grey2		= ImageColorAllocate($image, 100, 100, 100);
// Text einfügen

//                 size|an| X | Y                                   

//Top Left
ImageTTFText($image, 20, 0, 15, 30, $color_black, $font_text_m, $modules[0]["name"]);

// add battery icon
$baticon = imagecreatefrompng('./baticon/battery-' . $battery_status . '-64x64.png');
imagealphablending($baticon, false);
$baticon = imagerotate($baticon, 90, 0);
imagecopyresized($image, $baticon, 230, 0, 0, 0, 32, 32, 64, 64);
imagedestroy($baticon);

ImageTTFText($image, 60, 0, 80, 130, $color_black, $font_symbol, $conditionmapping[$icon]);

//Trend
$trend = "-";

if (strcasecmp($modules[0]["temp_trend"], "stable") == 0) {
	$trend = 2;
}
if (strcasecmp($modules[0]["temp_trend"], "down") == 0) {
	$trend = 1;
}
if (strcasecmp($modules[0]["temp_trend"], "up") == 0) {
	$trend = 0;
}


if (strlen($modules[0]["temp"]) < 4) {
	$modules[0]["temp"] =  $modules[0]["temp"];
	ImageTTFText($image, 45, 0, 80, 210, $color_black, $font_text_b, $modules[0]["temp"]);
	ImageTTFText($image, 45, 0, 80 + 110 - 32, 210, $color_black, $font_symbol, "c");
	ImageTTFText($image, 20, 0, 60 + 125 - 32, 210, $color_black, $font_symbol, $trend);
}
if (strlen($modules[0]["temp"]) == 4) {
	ImageTTFText($image, 45, 0, 80, 210, $color_black, $font_text_b, $modules[0]["temp"]);
	ImageTTFText($image, 45, 0, 80 + 110, 210, $color_black, $font_symbol, "c");
	ImageTTFText($image, 20, 0, 60 + 125 + 5, 210, $color_black, $font_symbol, $trend);
}
if (strlen($modules[0]["temp"]) > 4) {
	ImageTTFText($image, 45, 0, 80 - 22, 210, $color_black, $font_text_b, $modules[0]["temp"]);
	ImageTTFText($image, 45, 0, 80 + 110, 210, $color_black, $font_symbol, "c");
	ImageTTFText($image, 20, 0, 60 + 125, 210, $color_black, $font_symbol, $trend);
}


//pad pressure with additional space if it is only 3 digits long
$press = "";
if (strlen(number_format($modules[3]["pressure"], 0, "", "")) < 4) {
	$press = " " . number_format($modules[3]["pressure"], 0, "", "");
} else {
	$press = 	number_format($modules[3]["pressure"], 0, "", "");
}


ImageTTFText($image, 30, 0, 12, 250 + 5, $color_black, $font_text_b, $press);



$nachkomma = ltrim(number_format($modules[3]["pressure"] - floor($modules[3]["pressure"]), 1), "0");



ImageTTFText($image, 20, 0, 12 + 80 + 5, 250 + 5, $color_black, $font_text_b, $nachkomma);
ImageTTFText($image, 15, 0, 13, 270 + 5, $color_grey2, $font_text_m, "mBar Druck");

ImageTTFText($image, 30, 0, 166, 250 + 5, $color_black, $font_text_b, $modules[0]["humidity"]);
ImageTTFText($image, 20, 0, 166 + 42, 250 + 5, $color_black, $font_text_b, "%");
ImageTTFText($image, 15, 0, 149, 270 + 5, $color_grey2, $font_text_m, "Feuchtigkeit");


// Temp curve
ImageTTFText($image, 20, 0, 266 + 15, 30, $color_black, $font_text_m, "Temperaturverlauf 6h");


// Dte and time

date_default_timezone_set('Europe/Berlin');
$date = new DateTime();
ImageTTFText($image, 20, 0, 2 * 266 + 80, 30, $color_black, $font_text_m, "Messung vom:");
ImageTTFText($image, 18, 0, 2 * 266 + 105, 70, $color_black, $font_text_m, $date->format('d.m.Y'));
ImageTTFText($image, 18, 0, 2 * 266 + 135, 100, $color_black, $font_text_m, $date->format('H:i'));

//Modules

for ($i = 0; $i < 3; $i++) {
	ImageTTFText($image, 20, 0, $i * 266 + 15, 330, $color_white, $font_text_m, $modules[$i + 1]["name"]);

	// add battery icon
	$baticon = imagecreatefrompng('./baticon/battery-' . $modules[$i + 1]["battery_status"] . '-64x64.png');
	imagealphablending($baticon, false);
	$baticon = imagerotate($baticon, 90, 0);
	imagefilter($baticon, IMG_FILTER_NEGATE);
	imagecopyresized($image, $baticon, $i * 266 + 230, 300, 0, 0, 32, 32, 64, 64);
	imagedestroy($baticon);



	ImageTTFText($image, 45, 0, $i * 266 + 80, 400, $color_white, $font_text_b, $modules[$i + 1]["temp"]);
	//Centigrade
	ImageTTFText($image, 45, 0, $i * 266 + 80 + 110, 400, $color_white, $font_symbol, "c");


	//Trend
	$trend = "-";

	if (strcasecmp($modules[$i + 1]["temp_trend"], "stable") == 0) {
		$trend = 2;
	}
	if (strcasecmp($modules[$i + 1]["temp_trend"], "down") == 0) {
		$trend = 1;
	}
	if (strcasecmp($modules[$i + 1]["temp_trend"], "up") == 0) {
		$trend = 0;
	}
	ImageTTFText($image, 20, 0, $i * 266 + 60 + 125, 400, $color_white, $font_symbol, $trend);



	if ($modules[$i + 1]["co2"] > 1200 or $modules[$i + 1]["humidity"] > 60) {
		ImageTTFText($image, 40, 0, $i * 266 + 57, 465, $color_white, $font_text_b, "L&#252;ften");
	} else {
		ImageTTFText($image, 40, 0, $i * 266 + 80 + 10, 465, $color_white, $font_text_b, "Gut");
	}

	ImageTTFText($image, 15, 0, $i * 266 + 84, 485, $color_grey, $font_text_m, "Raumklima");


	if (strlen($modules[$i + 1]["co2"]) < 4) {
		$modules[$i + 1]["co2"] = " " . $modules[$i + 1]["co2"];
	}

	ImageTTFText($image, 30, 0, $i * 266 + 25, 550, $color_white, $font_text_b,  $modules[$i + 1]["co2"]);
	//ImageTTFText($image, 20, 0, $i*266+18+80, 550, $color_white, $font_text, ".$i");
	ImageTTFText($image, 15, 0, $i * 266 + 28, 570, $color_grey, $font_text_m, "ppm Co2");

	ImageTTFText($image, 30, 0, $i * 266 + 166, 550, $color_white, $font_text_b, $modules[$i + 1]["humidity"]);
	ImageTTFText($image, 20, 0, $i * 266 + 166 + 45, 550, $color_white, $font_text_b, "%");
	ImageTTFText($image, 15, 0, $i * 266 + 149, 570, $color_grey, $font_text_m, "Feuchtigkeit");
}



// getting 3 days forecast

$url = "http://api.openweathermap.org/data/2.5/forecast?id=6940468&cnt=24&lang=en&units=metric&APPID=951ffbd4db78f3909777ee2c0431da5e";

$contents = file_get_contents($url);
$clima = json_decode($contents);

//$icon=$clima->weather[0]->icon;
//print_r($clima);





// Hilfslinien einfügen
/*
	ImageFilledRectangle($image, 266, 0, 267, 600, $color_black);
	ImageFilledRectangle($image, 533, 0, 534, 600, $color_black);
	for ($i = 1; $i < 6; $i++) {
	
		ImageFilledRectangle($image, $i*133, 0, $i*133+1, 300, $color_black);
	}
	for ($i = 1; $i < 6; $i++) {
	
	ImageFilledRectangle($image, $i*133, 301, $i*133+1, 600, $color_white);
	}
	
	//ImageFilledRectangle($image, 0, 299 , 800, 400, $color_white);
	
		for ($i = 1; $i < 11; $i++) {
	
	ImageFilledRectangle($image, 0, 300+$i*30, 800, 300+$i*30+1,  $color_white);
	}
			for ($i = 1; $i < 11; $i++) {
	
	ImageFilledRectangle($image, 0, $i*30, 800, $i*30+1,  $color_black);
	}
*/

// PNG-erstellen und temporäre Daten löschen


$graph = imagecreatefrompng('6h.png');


imagecopymerge($image, $graph, 266, 50, 0, 0, 266, 250, 100);


imagedestroy($graph);


$image = imagerotate($image, 90, 0);

ImagePNG($image, $filename);
ImageDestroy($image);


// Farbraum in Graustufen ändern

//	$im = new Imagick();
//	$im->readImage($filename);
//	$im->setImageType(Imagick::IMGTYPE_GRAYSCALE);
//	$im->writeImage($filename);
shell_exec('convert weather-script-output.png   -colorspace LinearGray weather-script-output.png ');

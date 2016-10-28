<!DOCTYPE HTML>

<html>
	<head>
		<title>Contact | CSS3 Basket</title>
		<meta charset="utf-8" />
		<meta name="viewport" content="width=device-width, initial-scale=1" />
		<!--[if lte IE 8]><script src="assets/js/ie/html5shiv.js"></script><![endif]-->
		<link rel="stylesheet" href="assets/css/main.css" />
		<!--[if lte IE 8]><link rel="stylesheet" href="assets/css/ie8.css" /><![endif]-->
	</head>
	<body class="homepage">
		<div id="page-wrapper">

			<!-- Header -->
				<div id="header">
					<div class="container">

						<!-- Logo -->
							<div id="logo">
								<span class="pennant"><span class="icon fa-futbol-o"></span></span>
								<h1><a href="index.html">Basket</a></h1>
							</div>

						<!-- Nav -->
							<nav id="nav">
								<ul>
									<li><a href="index.html">Home</a></li>
									<li><a href="services.html">Services</a></li>
									<li><a href="apage.html">A Page</a></li>
									<li>
										<a href="#" class="icon fa-caret-down">Drop Down Menu</a>
										<ul>
											<li><a href="#">Example Menu</a></li>
											<li><a href="#">Example Menu</a></li>
											<li><a href="#">Example Menu</a></li>
											<li><a href="#">Example Menu</a></li>
											<li>
												<a href="#">Example Submenu</a>
												<ul>
													<li><a href="#">Example Menu</a></li>
													<li><a href="#">Example Menu</a></li>
													<li><a href="#">Example Menu</a></li>
													<li><a href="#">Example Menu</a></li>
												</ul>
											</li>
										</ul>
									</li>
									<li class="active"><a href="contact.php">Contact Page</a></li>
								</ul>
							</nav>

					</div>
				</div>

			<!-- Main -->
				<div id="main">
					<section class="container">
						<div class="row">
							<section class="8u 12u(mobile)">
								<h2>Contact Us</h2>
								<p>Lorem ipsum dolor sit amet, consectetur adipisicing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat.</p>
								<?php
									// Set-up these 3 parameters
									// 1. Enter the email address you would like the enquiry sent to
									// 2. Enter the subject of the email you will receive, when someone contacts you
									// 3. Enter the text that you would like the user to see once they submit the contact form
									$to = 'enter email address here';
									$subject = 'Enquiry from the website';
									$contact_submitted = 'Your message has been sent.';

									// Do not amend anything below here, unless you know PHP
									function email_is_valid($email) {
									  return preg_match('/^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,4}$/i',$email);
									}
									if (!email_is_valid($to)) {
									  echo '<p style="color: red;">You must set-up a valid (to) email address before this contact page will work.</p>';
									}
									if (isset($_POST['contact_submitted'])) {
										$return = "\r";
										$youremail = trim(htmlspecialchars($_POST['your_email']));
										$yourname = stripslashes(strip_tags($_POST['your_name']));
										$yourmessage = stripslashes(strip_tags($_POST['your_message']));
										$contact_name = "Name: ".$yourname;
										$message_text = "Message: ".$yourmessage;
										$user_answer = trim(htmlspecialchars($_POST['user_answer']));
										$answer = trim(htmlspecialchars($_POST['answer']));
										$message = $contact_name . $return . $message_text;
										$headers = "From: ".$youremail;
										if (email_is_valid($youremail) && !eregi("\r",$youremail) && !eregi("\n",$youremail) && $yourname != "" && $yourmessage != "" && substr(md5($user_answer),5,10) === $answer) {
										  mail($to,$subject,$message,$headers);
										  $yourname = '';
										  $youremail = '';
										  $yourmessage = '';
										  echo '<p style="color: blue;">'.$contact_submitted.'</p>';
										}
										else echo '<p style="color: red;">Please enter your name, a valid email address, your message and the answer to the simple maths question before sending your message.</p>';
									  }
									  $number_1 = rand(1, 9);
									  $number_2 = rand(1, 9);
									  $answer = substr(md5($number_1+$number_2),5,10);
								?>
								<form id="contact" action="contact.php" method="post">
								  <div class="form_settings">
									<p><span>Name</span><input class="contact" type="text" name="your_name" value="<?php echo $yourname; ?>" /></p>
									<p><span>Email Address</span><input class="contact" type="text" name="your_email" value="<?php echo $youremail; ?>" /></p>
									<p><span>Message</span><textarea class="contact textarea" rows="5" cols="50" name="your_message"><?php echo $yourmessage; ?></textarea></p>
									<p style="line-height: 1.7em;">To help prevent spam, please enter the answer to this question:</p>
									<p><span><?php echo $number_1; ?> + <?php echo $number_2; ?> = ?</span><input type="text" name="user_answer" /><input type="hidden" name="answer" value="<?php echo $answer; ?>" /></p>
									<p style="padding-top: 15px"><span>&nbsp;</span><input class="submit" type="submit" name="contact_submitted" value="send" /></p>
								  </div>
								</form>
							</section>						
							<section class="4u 12u(mobile)">
								<div class="row" id="sidebar">
									<section class="12u">
										<h2>Latest News</h2>
										<h4>New Website Launched</h4>
										<h5>March 1st, 2016</h5>
										<p>2014 sees the redesign of our website. <a href="#">Read more</a></p>
										
										<h3>Useful Links</h3>
										<ul>
											<li><a href="#">First Link</a></li>
											<li><a href="#">Another Link</a></li>
											<li><a href="#">And Another</a></li>
											<li><a href="#">Last One</a></li>
										</ul>
										
										<h3>More Useful Links</h3>
										<ul>
											<li><a href="#">First Link</a></li>
											<li><a href="#">Another Link</a></li>
											<li><a href="#">And Another</a></li>
											<li><a href="#">Last One</a></li>
										</ul>
									</section>
								</div>
							</section>
						</div>	
					</section>
				</div>

			<!-- Footer -->
				<div id="footer">
					<div class="container">
						<section>
							<div class="row">
								<div class="3u 12u(mobile)">
									<header>
										<h2>Heading</h2>
									</header>
									<p>Lorem ipsum dolor sit amet, consectetur adipiscing elit. Curabitur sit amet egestas eros. Sed venenatis est nunc, id convallis tellus venenatis non. Proin id nisi euismod, molestie nisl vel, accumsan sem. Integer felis sem, lacinia eu auctor eget, dapibus feugiat elit. Duis lectus justo, ultrices ac placerat non, sollicitudin at massa.</p>
									<a href="#" class="button">More</a>
								</div>
								<div class="3u 12u(mobile)">
									<header>
										<h2>Heading</h2>
									</header>
									<p>Lorem ipsum dolor sit amet, consectetur adipiscing elit. Curabitur sit amet egestas eros. Sed venenatis est nunc, id convallis tellus venenatis non. Proin id nisi euismod, molestie nisl vel, accumsan sem. Integer felis sem, lacinia eu auctor eget, dapibus feugiat elit. Duis lectus justo, ultrices ac placerat non, sollicitudin at massa.</p>
									<a href="#" class="button">More</a>								
								</div>
								<div class="3u 12u(mobile)">
									<header>
										<h2>Heading</h2>
									</header>
									<p>Lorem ipsum dolor sit amet, consectetur adipiscing elit. Curabitur sit amet egestas eros. Sed venenatis est nunc, id convallis tellus venenatis non. Proin id nisi euismod, molestie nisl vel, accumsan sem. Integer felis sem, lacinia eu auctor eget, dapibus feugiat elit. Duis lectus justo, ultrices ac placerat non, sollicitudin at massa.</p>
									<a href="#" class="button">More</a>								
								</div>
								<div class="3u 12u(mobile)">
									<header>
										<h2>Heading</h2>
									</header>
									<p>Lorem ipsum dolor sit amet, consectetur adipiscing elit. Curabitur sit amet egestas eros. Sed venenatis est nunc, id convallis tellus venenatis non. Proin id nisi euismod, molestie nisl vel, accumsan sem. Integer felis sem, lacinia eu auctor eget, dapibus feugiat elit. Duis lectus justo, ultrices ac placerat non, sollicitudin at massa.</p>
									<a href="#" class="button">More</a>								
								</div>
							</div>								
						</section>

						<!-- Social -->
							<section>
								<ul class="icons">
									<li><a href="#" class="icon fa-twitter"><span>Twitter</span></a></li>
									<li><a href="#" class="icon fa-facebook"><span>Facebook</span></a></li>
									<li><a href="#" class="icon fa-google-plus"><span>Google+</span></a></li>
									<li><a href="#" class="icon fa-linkedin"><span>Linkedin</span></a></li>
									<li><a href="#" class="icon fa-pinterest"><span>Pinterest</span></a></li>
								</ul>
							</section>

						<!-- Copyright -->
							<div class="copyright">
								&copy; CSS3_Basket | <a href="http://www.css3templates.co.uk">a css3templates.co.uk design</a>								
							</div>

					</div>
				</div>

		</div>

		<!-- Scripts -->
			<script src="assets/js/jquery.min.js"></script>
			<script src="assets/js/jquery.dropotron.min.js"></script>
			<script src="assets/js/skel.min.js"></script>
			<script src="assets/js/util.js"></script>
			<!--[if lte IE 8]><script src="assets/js/ie/respond.min.js"></script><![endif]-->
			<script src="assets/js/main.js"></script>

	</body>
</html>
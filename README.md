This repo is made for Area Chairs of conferences that use OpenReview.  
Tired of having to manually copy ratings from OpenReview to your tracker spreadsheet?  
**Tire no more!**

This repo will render a summary of the papers in your AC batch:  
<img src="demo.png" alt="Sample output" width="500"/>


<!-- **Try it in Google Colab -** [link](https://colab.research.google.com/drive/1wv1ayx1f0TScy7_IWFmNJMPx84El9wr4?usp=sharing) -->

Or locally,
### Step 0:
Create a virtualenv, install dependencies.
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Step 1:
Enter your OpenReview credentials in the .env file.
```
USERNAME=<YOUR-USERNAME>
PASSWORD=<YOUR-PASSWORD>
```

### Step 2: 
Run the script to log into your account, gather submission info, and print it.

For CVPR 2026, try this:
```bash
>> python run.py --conf cvpr_2026 --headless

Opening https://openreview.net/group?id=thecvf.com/CVPR/2026/Conference/Area_Chairs
Logging in.
Waiting for page to finish loading...
Logged in.
Found 15 submissions.
1, 1234, To boop or not to boop?, 2, 3
...
15, 214, Ursidae are all you need, 4, 4
```

Skip `--headless` if you want to watch it do the web navigation.  
You can skip reviews with the `--skip_reviews` flag.

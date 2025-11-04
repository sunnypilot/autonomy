# Driving Policy Model Merge Module

* Want to figure out how to freaking merge policy driving models? 
* Well don't dilly dally! You came to the right place. 
## 
* Here at sunnypilot autonomy we created a script that does the heavy work for you!

* But how does this freaking thing work?

* Well, all you have to do is place your two policy models in the supplied model1 and model2 directories. after that simply run the merge script and it handles the rest with default weight of 0.5.

* How do I run the script????
##

```
python3 -m driving_model_scripts.merge
```
* It's that easy. It handles model validation, model merging and unittesting all by it self with no user interference needed. 
* After merging your model, test it on metadrive simulator!
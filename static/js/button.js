var example = document.getElementById("enabled")
for (var i = 0, max = example.length; i < max; i++)
{
    if(example[i].innerText == "True")
    {
        alert(example[i].innerText)
        example[i].innerText = "Online"
    }
    
    if(example[i].innerText == "False")
    {
        example[i].innerText = "Offline"
    }
}

function Clone() {
    var clone = document.getElementById('thediv').cloneNode(true); // "deep" clone
    document.getElementById("container").appendChild(clone);
  }
  
function Delete(button) {
    var parent = document.getElementById("thediv").parentNode;
    var grand_father = document.getElementById("container").parentNode;;
    grand_father.removeChild(parent);
  }
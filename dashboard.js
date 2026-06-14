// Dashboard JavaScript - saccosystem2
function submitForm(form,action){
 const data = {};
 new FormData(form).forEach((v,k)=>data[k]=v);
 
 const today = new Date().toISOString().split('T')[0];
 if(action === 'add_tx' && data.date > today){
   if(!confirm('Transaction date is in the future. Continue anyway?')) return false;
 }
 if(action === 'add_member'){
   if(data.joined_date > today){
     if(!confirm('Join date is in the future. Continue anyway?')) return false;
   }
 }

 // Registration check
 if(action === 'add_tx' && data.type === 'registration'){
   fetch('/check_registration',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({member_id:data.member_id})})
   .then(function(r){return r.json();})
   .then(function(j){
     if(j.has_registration && !confirm('This member already has a registration fee. Add another anyway?')){
       return;
     }
     doSubmit(action, data);
   });
   return false;
 }

 doSubmit(action, data);
 return false;
}

function doSubmit(action, data){
 fetch('/'+action,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)})
 .then(function(r){return r.json();})
 .then(function(j){
   const msg = document.getElementById('msg');
   msg.className = 'msg ok';
   msg.textContent = j.status === 'ok' ? 'Success!' : j.message || JSON.stringify(j);
   
   // If loan_disbursement, upload evidence file
   if(j.status === 'ok' && data.type === 'loan_disbursement' && j.tx_id){
     var fileInput = document.getElementById('evidence-file');
     if(fileInput && fileInput.files && fileInput.files[0]){
       uploadEvidence(j.tx_id, fileInput.files[0]);
     }
   }
   
   if(j.status === 'ok' && (action === 'add_member' || action === 'delete_tx')){
     setTimeout(function(){location.reload();}, 1200);
   }
 })
 .catch(function(e){
   document.getElementById('msg').className='msg err';
   document.getElementById('msg').textContent='Error: '+e.message;
 });
}

function uploadEvidence(txId, file){
 var reader = new FileReader();
 reader.onload = function(e){
   var base64Data = e.target.result.split(',')[1];
   fetch('/upload_evidence',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({tx_id:txId,file_data:base64Data})})
   .then(function(r){return r.json();})
   .then(function(j){
     var msg = document.getElementById('msg');
     if(j.status === 'ok'){
       msg.textContent += ' (PDF uploaded)';
     }
   });
 };
 reader.readAsDataURL(file);
}

// Show evidence upload when loan_disbursement is selected
document.addEventListener('change', function(e){
 if(e.target && e.target.name === 'type' && e.target.value === 'loan_disbursement'){
   document.getElementById('evidence-upload').style.display = 'block';
 } else if(e.target && e.target.name === 'type'){
   document.getElementById('evidence-upload').style.display = 'none';
 }
});

function sendStatements(){
 const btn = document.querySelector('.send');
 const status = document.getElementById('send-status');
 btn.disabled = true;
 status.textContent = 'Sending statements...';
 fetch('/send_all_statements',{method:'POST'})
 .then(function(r){return r.json();})
 .then(function(j){ 
   if(j.status === 'started'){
     status.textContent = j.message;
     setTimeout(function(){ btn.disabled = false; }, 3000);
   } else {
     status.textContent = 'Sent to ' + j.sent + ' member(s)'; 
     btn.disabled = false;
   }
 })
 .catch(function(e){ status.textContent = 'Error: '+e.message; btn.disabled = false; });
}

function editMember(id,name,email,phone,number,dob){
 document.getElementById('edit-id').value = id;
 document.getElementById('edit-name').value = name;
 document.getElementById('edit-email').value = email;
 document.getElementById('edit-phone').value = phone;
 document.getElementById('edit-number').value = number;
 document.getElementById('edit-dob').value = dob;
 document.getElementById('editModal').style.display = 'flex';
}
function closeEdit(){
 document.getElementById('editModal').style.display = 'none';
}
function saveMember(){
 const id = document.getElementById('edit-id').value;
 const fields = ['name','email','phone','member_number','dob'];
 const msg = document.getElementById('msg');
 Promise.all(fields.map(function(f){
   const v = document.getElementById('edit-'+(f==='member_number'?'number':f)).value;
   if(v) return fetch('/edit_member',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({member_id:id,field:f,value:v})});
 })).then(function(){
   msg.className = 'msg ok';
   msg.textContent = 'Member updated!';
   closeEdit();
   setTimeout(function(){location.reload();}, 1500);
 }).catch(function(e){
   msg.className = 'msg err';
   msg.textContent = 'Error: '+e.message;
 });
}

var txTypes = ['contribution','loan_disbursement','loan_repayment','share_purchase','registration','refund'];

function editTx(id, date, type, amount){
 var amtFmt = parseFloat(amount).toFixed(2);
 var row = document.getElementById('txrow-'+id);
 row.innerHTML = "<td><input id='ed-"+id+"-date' value='"+date+"' style='width:90px;font-size:13px;'></td>" +
   "<td><select id='ed-"+id+"-type' style='font-size:13px;'>" +
   txTypes.map(function(t){return "<option value='"+t+"'"+(t==type?" selected":"")+">"+t.replace(/_/g,' ')+"</option>"}).join('') +
   "</select></td>" +
   "<td><input id='ed-"+id+"-amt' value='"+amtFmt+"' style='width:80px;text-align:right;font-size:13px;'></td>" +
   "<td><button class='edit-btn' onclick='saveTx(\""+id+"\")'>Save</button> " +
   "<button class='del-btn' onclick='viewTx(document.getElementById(\"tx-viewer\").dataset.mid,document.getElementById(\"tx-viewer\").dataset.mname)'>X</button></td>";
}

function saveTx(id){
 var date = document.getElementById('ed-'+id+'-date').value;
 var type = document.getElementById('ed-'+id+'-type').value;
 var amt = document.getElementById('ed-'+id+'-amt').value;
 fetch('/edit_tx',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({tx_id:id,date:date,type:type,amount:parseFloat(amt)})})
 .then(function(){
   document.getElementById('msg').className = 'msg ok';
   document.getElementById('msg').textContent = 'Transaction updated!';
   var v = document.getElementById('tx-viewer');
   viewTx(v.dataset.mid, v.dataset.mname);
 });
}

// Filter functions
var currentFilterMember = '';
var currentFilterName = '';

function viewTx(mid, name){
 currentFilterMember = mid;
 currentFilterName = name;
 var v = document.getElementById('tx-viewer');
 v.dataset.mid = mid;
 v.dataset.mname = name;
 loadFilteredTx(mid, name);
}

function loadFilteredTx(mid, name){
var filters = {member_id: mid};
document.getElementById('filter-bar').style.display = 'block';
 
 var ft = document.getElementById('filter-type');
 var famin = document.getElementById('filter-amt-min');
 var famax = document.getElementById('filter-amt-max');
 var fdfrom = document.getElementById('filter-date-from');
 var fdto = document.getElementById('filter-date-to');
 
 if(ft && ft.value) filters.filter_type = ft.value;
 if(famin && famin.value) filters.filter_amt_min = famin.value;
 if(famax && famax.value) filters.filter_amt_max = famax.value;
 if(fdfrom && fdfrom.value) filters.filter_date_from = fdfrom.value;
 if(fdto && fdto.value) filters.filter_date_to = fdto.value;
 
 fetch('/member_tx',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(filters)})
 .then(function(r){return r.json();})
 .then(function(j){
   document.getElementById('tx-title').textContent = 'Transactions: ' + name + ' (' + j.count + ')';
   document.getElementById('tx-content').innerHTML = '<table style="width:100%;font-size:13px;"><tr style="background:#ddd;"><th>Date</th><th>Type</th><th style="text-align:right;">Amount</th><th></th></tr>' + j.html + '</table>';
   document.getElementById('tx-viewer').style.display = 'block';
 });
}

function applyFilters(){
 loadFilteredTx(currentFilterMember, currentFilterName);
}

function clearFilters(){
 document.getElementById('filter-type').value = '';
 document.getElementById('filter-amt-min').value = '';
 document.getElementById('filter-amt-max').value = '';
 document.getElementById('filter-date-from').value = '';
 document.getElementById('filter-date-to').value = '';
 applyFilters();
}

function closeTxViewer(){
 document.getElementById('tx-viewer').style.display = 'none';
 document.getElementById('filter-bar').style.display = 'none';
}

function deleteMember(mid, name){
 if(!confirm('Delete member ' + name + '? This will also delete all their transactions.')) return;
 document.getElementById('msg').className = 'msg ok';
 document.getElementById('msg').textContent = 'Deleting ' + name + '...';
 fetch('/delete_member',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({member_id:mid})})
 .then(function(){ location.reload(); });
}

function toggleHelp(){
 var s = document.getElementById('help-section');
 s.style.display = s.style.display === 'none' ? 'block' : 'none';
}
function toggleActivity(){
 var s = document.getElementById('activity-section');
 if(s.style.display === 'none'){
   s.style.display = 'block';
   fetch('/get_activity',{method:'POST'})
   .then(function(r){return r.json();})
   .then(function(j){
     document.getElementById('activity-content').innerHTML =
       '<table style="width:100%;font-size:12px;">' +
       '<tr><td><strong>Members</strong></td><td>'+j.total_members+'</td></tr>' +
       '<tr><td><strong>Transactions</strong></td><td>'+j.total_transactions+'</td></tr>' +
       '<tr><td><strong>Statements sent</strong></td><td>'+j.total_statements_sent+'</td></tr>' +
       '<tr><td style="padding-top:10px;"><strong>Last transaction</strong></td><td style="padding-top:10px;">'+j.last_transaction+'</td></tr>' +
       '<tr><td><strong>Last member added</strong></td><td>'+j.last_member+'</td></tr>' +
       '<tr><td><strong>Last statement sent</strong></td><td>'+j.last_statement_sent+'</td></tr>' +
       '<tr><td><strong>Last settings change</strong></td><td>'+j.last_settings_update+'</td></tr>' +
       '</table>';
   });
 } else {
   s.style.display = 'none';
 }
}
function toggleSettings(){
 var s = document.getElementById('settings-section');
 s.style.display = s.style.display === 'none' ? 'block' : 'none';
}
function saveSettings(){
 const keys = ['sender_name','sender_email','society_name','account_type','interest_rate','gmail_app_password'];
 const data = {};
 keys.forEach(function(k){ data[k] = document.getElementById('set-'+k).value; });
 const msg = document.getElementById('settings-msg');
 fetch('/update_settings',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)})
 .then(function(r){return r.json();})
 .then(function(j){ msg.textContent = 'Settings saved!'; msg.style.color = '#27ae60'; })
 .catch(function(e){ console.error('Settings save error', e); });
}
function shutdownSystem(){
 if(!confirm('Shut down the SACCO system?')) return;
 fetch('/shutdown',{method:'POST'});
 document.body.innerHTML = '<div style="text-align:center;margin-top:100px;font-family:Arial;"><h2>System shut down</h2><p>You can close this tab.</p></div>';
}
function testEmail(){
 const to = document.getElementById('test-email-to').value;
 if(!to) return;
 const msg = document.getElementById('test-msg');
 msg.textContent = 'Sending test...';
 msg.style.color = '#999';
 fetch('/test_email_settings',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({to:to})})
 .then(function(r){return r.json();})
 .then(function(j){
   if(j.status === 'ok'){
     msg.textContent = 'Test sent! Check your inbox.';
     msg.style.color = '#27ae60';
   } else {
     msg.textContent = 'Failed: '+j.message;
     msg.style.color = '#e74c3c';
   }
 })
 .catch(function(e){ console.error('Test email error', e); });
}
